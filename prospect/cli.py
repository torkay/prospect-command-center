"""
Prospect Scraper CLI - Power User Edition

Examples:
    # Basic search
    prospect search "plumber" "Sydney"

    # JSON output, piped to jq
    prospect search "accountant" "Brisbane" -f json -q | jq '.[:5]'

    # Fast mode (no enrichment)
    prospect search "lawyer" "Melbourne" --skip-enrichment

    # Filtered results
    prospect search "buyer's agent" "Brisbane" --min-fit 50 --require-phone

    # Batch processing
    prospect batch queries.txt -o results/

    # Debug mode
    prospect search "electrician" "Adelaide" --debug --save-raw

    # Check configuration
    prospect check
"""

import asyncio
import csv
import io
import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

from .config import ScraperConfig, Settings, load_config
from .models import Prospect
from .scraper.serpapi import SerpAPIClient, AuthenticationError as SerpAuthError, SerpAPIError
from .dedup import deduplicate_serp_results
from .enrichment.crawler import WebsiteCrawler
from .scoring import calculate_fit_score, calculate_opportunity_score, generate_opportunity_notes
from .export import export_prospects
from .sheets import SheetsExporter, SheetsError, AuthenticationError as SheetsAuthError

# Progress to stderr, data to stdout
console = Console(stderr=True)
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool, quiet: bool, debug: bool) -> None:
    """Configure logging based on CLI flags."""
    if quiet:
        level = logging.ERROR
    elif debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def format_output(
    prospects: list[Prospect],
    output_format: str,
    no_headers: bool = False,
) -> str:
    """Format prospects for output."""
    if output_format == "json":
        return json.dumps([p.to_dict() for p in prospects], indent=2, default=str)

    elif output_format == "jsonl":
        return "\n".join(json.dumps(p.to_dict(), default=str) for p in prospects)

    elif output_format in ("csv", "tsv"):
        delimiter = "\t" if output_format == "tsv" else ","
        output = io.StringIO()

        fieldnames = [
            "name", "domain", "phone", "emails", "rating", "reviews",
            "fit_score", "opportunity_score", "priority_score",
            "opportunity_notes", "website", "address",
            "in_ads", "in_maps", "in_organic", "cms", "has_analytics"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)

        if not no_headers:
            writer.writeheader()

        for p in prospects:
            # Get signals data if available
            signals = p.signals
            cms = signals.cms if signals else ""
            has_analytics = signals.has_google_analytics if signals else False

            writer.writerow({
                "name": p.name or "",
                "domain": p.domain or "",
                "phone": p.phone or "",
                "emails": ";".join(p.emails) if p.emails else "",
                "rating": p.rating or "",
                "reviews": p.review_count or "",
                "fit_score": p.fit_score,
                "opportunity_score": p.opportunity_score,
                "priority_score": round(p.priority_score, 1),
                "opportunity_notes": p.opportunity_notes or "",
                "website": p.website or "",
                "address": p.address or "",
                "in_ads": "1" if p.found_in_ads else "0",
                "in_maps": "1" if p.found_in_maps else "0",
                "in_organic": "1" if p.found_in_organic else "0",
                "cms": cms or "",
                "has_analytics": "1" if has_analytics else "0",
            })

        return output.getvalue()

    else:
        raise ValueError(f"Unknown format: {output_format}")


def display_summary(prospects: list[Prospect]) -> None:
    """Display a summary table of top prospects."""
    table = Table(title="Top Prospects", show_header=True, header_style="bold magenta")

    table.add_column("Name", style="cyan", max_width=30)
    table.add_column("Fit", justify="right")
    table.add_column("Opp", justify="right")
    table.add_column("Priority", justify="right")
    table.add_column("SERP", justify="center")
    table.add_column("Key Opportunity", max_width=40)

    for p in prospects:
        # Build SERP presence indicator
        serp_parts = []
        if p.found_in_ads:
            serp_parts.append("A")
        if p.found_in_maps:
            serp_parts.append("M")
        if p.found_in_organic:
            serp_parts.append("O")
        serp = "/".join(serp_parts) or "-"

        # Get first opportunity note
        notes = p.opportunity_notes.split(";")[0].strip() if p.opportunity_notes else "-"

        # Color code scores
        fit_color = "green" if p.fit_score >= 70 else "yellow" if p.fit_score >= 40 else "red"
        opp_color = "green" if p.opportunity_score >= 70 else "yellow" if p.opportunity_score >= 40 else "red"
        priority_color = "green" if p.priority_score >= 70 else "yellow" if p.priority_score >= 40 else "red"

        table.add_row(
            p.name[:30],
            f"[{fit_color}]{p.fit_score}[/{fit_color}]",
            f"[{opp_color}]{p.opportunity_score}[/{opp_color}]",
            f"[{priority_color}]{p.priority_score:.0f}[/{priority_color}]",
            serp,
            notes[:40],
        )

    console.print(table)
    console.print("\n[dim]SERP: A=Ads, M=Maps, O=Organic[/dim]")


# ============================================================================
# CLI Group
# ============================================================================

@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version="1.0.0")
def cli(ctx):
    """Prospect discovery tool for finding businesses that need marketing help."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ============================================================================
# Search Command
# ============================================================================

@cli.command()
@click.argument("business_type")
@click.argument("location")
@click.option("-l", "--limit", default=20, help="Max prospects to find")
@click.option("-o", "--output", type=click.Path(), help="Output file (default: stdout)")
@click.option("-f", "--format", "output_format",
              type=click.Choice(["csv", "json", "jsonl", "tsv"]),
              default="csv", help="Output format")
@click.option("-q", "--quiet", is_flag=True, help="Suppress progress, only emit data")
@click.option("-v", "--verbose", is_flag=True, help="Verbose debug output")
@click.option("--no-headers", is_flag=True, help="Omit headers in CSV/TSV")
# Filtering
@click.option("--min-fit", type=int, default=0, help="Minimum fit score")
@click.option("--min-opportunity", type=int, default=0, help="Minimum opportunity score")
@click.option("--min-priority", type=float, default=0, help="Minimum priority score")
@click.option("--require-phone", is_flag=True, help="Must have phone number")
@click.option("--require-email", is_flag=True, help="Must have email")
@click.option("--exclude-domain", multiple=True, help="Exclude domain (repeatable)")
# Performance
@click.option("--skip-enrichment", is_flag=True, help="Skip website analysis")
@click.option("-j", "--parallel", type=int, default=1, help="Parallel workers (not yet implemented)")
@click.option("--timeout", type=int, default=10, help="Fetch timeout (seconds)")
# Scoring
@click.option("--config", type=click.Path(exists=True), help="YAML config file")
@click.option("--fit-weight", type=float, default=0.4, help="Fit weight in priority")
@click.option("--opportunity-weight", type=float, default=0.6, help="Opportunity weight")
# Debug
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.option("--dry-run", is_flag=True, help="Show plan without executing")
@click.option("--save-raw", is_flag=True, help="Save raw SERP response")
# Export
@click.option("--sheets", is_flag=True, help="Export to Google Sheets")
@click.option("--sheets-name", help="Google Sheet name")
@click.option("--sheets-append", help="Append to existing sheet (provide sheet ID)")
@click.option("--sheets-share", multiple=True, help="Email to share sheet with (repeatable)")
def search(
    business_type: str,
    location: str,
    limit: int,
    output: Optional[str],
    output_format: str,
    quiet: bool,
    verbose: bool,
    no_headers: bool,
    min_fit: int,
    min_opportunity: int,
    min_priority: float,
    require_phone: bool,
    require_email: bool,
    exclude_domain: tuple,
    skip_enrichment: bool,
    parallel: int,
    timeout: int,
    config: Optional[str],
    fit_weight: float,
    opportunity_weight: float,
    debug: bool,
    dry_run: bool,
    save_raw: bool,
    sheets: bool,
    sheets_name: Optional[str],
    sheets_append: Optional[str],
    sheets_share: tuple,
):
    """
    Search for prospects matching criteria.

    Output goes to stdout by default (use -o for file).
    Progress goes to stderr (use -q to suppress).

    Examples:

        prospect search "plumber" "Sydney"

        prospect search "accountant" "Brisbane" -f json -q | jq '.'

        prospect search "buyer's agent" "Brisbane" --min-fit 50 --require-phone
    """
    setup_logging(verbose, quiet, debug)

    # Load config
    settings = load_config(config) if config else Settings()

    # Dry run
    if dry_run:
        click.echo(f"Would search: '{business_type}' in '{location}'")
        click.echo(f"Limit: {limit}, Format: {output_format}")
        click.echo(f"Filters: min_fit={min_fit}, min_opp={min_opportunity}, min_priority={min_priority}")
        click.echo(f"Enrichment: {'skip' if skip_enrichment else 'enabled'}")
        sys.exit(0)

    scraper_config = ScraperConfig(debug=debug)
    prospects: list[Prospect] = []

    # Use progress context only when not quiet
    if quiet:
        # Silent execution
        try:
            with SerpAPIClient() as client:
                serp_results = client.search(business_type, location, num_results=limit)
        except SerpAuthError as e:
            console.print(f"[red]SerpAPI auth error:[/red] {e}", file=sys.stderr)
            sys.exit(1)
        except SerpAPIError as e:
            console.print(f"[red]SerpAPI error:[/red] {e}", file=sys.stderr)
            sys.exit(1)

        # Save raw if requested
        if save_raw:
            raw_path = Path(f"raw_{business_type.replace(' ', '_')}_{location.replace(' ', '_')}.json")
            raw_data = {
                "query": serp_results.query,
                "location": serp_results.location,
                "ads": len(serp_results.ads),
                "maps": len(serp_results.maps),
                "organic": len(serp_results.organic),
            }
            raw_path.write_text(json.dumps(raw_data, indent=2))

        # Deduplicate (pass location for phone validation)
        prospects = deduplicate_serp_results(serp_results, location=location)

        # Filter by excluded domains
        if exclude_domain:
            exclude_set = set(d.lower() for d in exclude_domain)
            prospects = [p for p in prospects if not p.domain or p.domain.lower() not in exclude_set]

        # Enrich
        if not skip_enrichment and prospects:
            async def enrich_all():
                async with WebsiteCrawler(scraper_config) as crawler:
                    for prospect in prospects:
                        try:
                            await crawler.enrich_prospect(prospect)
                        except Exception as e:
                            logger.debug("Failed to enrich %s: %s", prospect.name, e)

            asyncio.run(enrich_all())

        # Score
        for prospect in prospects:
            prospect.fit_score = calculate_fit_score(prospect)
            prospect.opportunity_score = calculate_opportunity_score(prospect)
            prospect.priority_score = (
                prospect.fit_score * fit_weight +
                prospect.opportunity_score * opportunity_weight
            )
            prospect.opportunity_notes = generate_opportunity_notes(prospect)

    else:
        # With progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            # Step 1: Search
            search_task = progress.add_task("[cyan]Searching via SerpAPI...", total=1)

            try:
                with SerpAPIClient() as client:
                    serp_results = client.search(business_type, location, num_results=limit)
            except SerpAuthError as e:
                progress.stop()
                console.print(f"\n[red]Authentication Error:[/red] {e}")
                console.print("\n[yellow]To set up SerpAPI:[/yellow]")
                console.print("  1. Sign up at [link=https://serpapi.com/]https://serpapi.com/[/link]")
                console.print("  2. Copy your API key from the dashboard")
                console.print("  3. Set it: [cyan]export SERPAPI_KEY=your_key_here[/cyan]")
                sys.exit(1)
            except SerpAPIError as e:
                progress.stop()
                console.print(f"\n[red]SerpAPI Error:[/red] {e}")
                sys.exit(1)

            progress.update(search_task, completed=1)

            # Save raw if requested
            if save_raw:
                raw_path = Path(f"raw_{business_type.replace(' ', '_')}_{location.replace(' ', '_')}.json")
                raw_data = {
                    "query": serp_results.query,
                    "location": serp_results.location,
                    "ads": len(serp_results.ads),
                    "maps": len(serp_results.maps),
                    "organic": len(serp_results.organic),
                }
                raw_path.write_text(json.dumps(raw_data, indent=2))
                console.print(f"[dim]Saved raw: {raw_path}[/dim]")

            console.print(
                f"[green]Found:[/green] {len(serp_results.ads)} ads, "
                f"{len(serp_results.maps)} maps, {len(serp_results.organic)} organic"
            )

            # Step 2: Deduplicate (pass location for phone validation)
            dedup_task = progress.add_task("[cyan]Deduplicating...", total=1)
            prospects = deduplicate_serp_results(serp_results, location=location)
            progress.update(dedup_task, completed=1)

            # Filter by excluded domains
            if exclude_domain:
                exclude_set = set(d.lower() for d in exclude_domain)
                prospects = [p for p in prospects if not p.domain or p.domain.lower() not in exclude_set]

            console.print(f"[green]Unique prospects:[/green] {len(prospects)}")

            if not prospects:
                console.print(
                    "[yellow]No prospects found.[/yellow]\n"
                    "[dim]Possible causes:[/dim]\n"
                    "  - No results for this search term/location\n"
                    "  - Try different keywords or broader location"
                )
                sys.exit(1)

            # Step 3: Enrich
            if not skip_enrichment:
                enrich_task = progress.add_task(
                    "[cyan]Enriching prospects...",
                    total=len(prospects),
                )

                async def enrich_all():
                    async with WebsiteCrawler(scraper_config) as crawler:
                        for i, prospect in enumerate(prospects):
                            try:
                                await crawler.enrich_prospect(prospect)
                            except Exception as e:
                                logger.debug("Failed to enrich %s: %s", prospect.name, e)
                            progress.update(enrich_task, completed=i + 1)

                asyncio.run(enrich_all())

            # Step 4: Score
            score_task = progress.add_task("[cyan]Scoring prospects...", total=len(prospects))

            for i, prospect in enumerate(prospects):
                prospect.fit_score = calculate_fit_score(prospect)
                prospect.opportunity_score = calculate_opportunity_score(prospect)
                prospect.priority_score = (
                    prospect.fit_score * fit_weight +
                    prospect.opportunity_score * opportunity_weight
                )
                prospect.opportunity_notes = generate_opportunity_notes(prospect)
                progress.update(score_task, completed=i + 1)

    # Sort by priority score
    prospects.sort(key=lambda p: p.priority_score, reverse=True)

    # Apply filters
    if min_fit:
        prospects = [p for p in prospects if p.fit_score >= min_fit]
    if min_opportunity:
        prospects = [p for p in prospects if p.opportunity_score >= min_opportunity]
    if min_priority:
        prospects = [p for p in prospects if p.priority_score >= min_priority]
    if require_phone:
        prospects = [p for p in prospects if p.phone]
    if require_email:
        prospects = [p for p in prospects if p.emails]

    # Limit results
    prospects = prospects[:limit]

    if not quiet:
        console.print(f"[dim]{len(prospects)} prospects after filtering[/dim]")

    # Google Sheets export
    if sheets or sheets_append:
        try:
            exporter = SheetsExporter()

            if sheets_append:
                if not quiet:
                    console.print(f"\n[blue]Appending to Google Sheet...[/blue]")
                sheet_url = exporter.append(prospects, sheet_id=sheets_append)
            else:
                if not quiet:
                    console.print(f"\n[blue]Creating Google Sheet...[/blue]")
                sheet_url = exporter.export(
                    prospects,
                    name=sheets_name,
                    share_with=list(sheets_share) if sheets_share else None,
                )

            if not quiet:
                console.print(f"[green]Google Sheet:[/green] {sheet_url}")

        except SheetsAuthError as e:
            console.print(f"\n[red]Google Sheets authentication error:[/red]")
            console.print(str(e))
        except SheetsError as e:
            console.print(f"\n[red]Google Sheets error:[/red] {e}")

    # Output
    if output:
        # Write to file
        output_path = export_prospects(prospects, output, output_format.replace("jsonl", "json"))
        if not quiet:
            console.print(f"\n[green]Saved:[/green] {output_path}")
            display_summary(prospects[:10])
    else:
        # Output to stdout
        output_data = format_output(prospects, output_format, no_headers)
        click.echo(output_data)

    # Exit code: 0 if results, 1 if empty
    sys.exit(0 if prospects else 1)


# ============================================================================
# Batch Command
# ============================================================================

@cli.command()
@click.argument("queries_file", type=click.Path(exists=True))
@click.option("-o", "--output-dir", type=click.Path(), default=".", help="Output directory")
@click.option("-f", "--format", "output_format",
              type=click.Choice(["csv", "json"]), default="csv")
@click.option("--skip-enrichment", is_flag=True, help="Skip website analysis")
@click.option("-q", "--quiet", is_flag=True, help="Minimal output")
def batch(queries_file: str, output_dir: str, output_format: str, skip_enrichment: bool, quiet: bool):
    """
    Run multiple searches from a file.

    File format: one query per line as "business_type|location"

    Example file:

        plumber|Sydney, NSW

        electrician|Melbourne, VIC

        buyer's agent|Brisbane, QLD
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Parse queries
    queries = []
    with open(queries_file) as f:
        for line in f:
            line = line.strip()
            if line and "|" in line:
                business_type, location = line.split("|", 1)
                queries.append((business_type.strip(), location.strip()))

    if not quiet:
        console.print(f"[dim]Loaded {len(queries)} queries[/dim]")

    success_count = 0
    for business_type, location in queries:
        safe_name = f"{business_type.replace(' ', '_')}_{location.replace(' ', '_').replace(',', '')}"
        output_file = output_path / f"{safe_name}.{output_format}"

        if not quiet:
            console.print(f"[dim]Processing: {business_type} in {location}[/dim]")

        try:
            # Search
            with SerpAPIClient() as client:
                serp_results = client.search(business_type, location, num_results=20)

            prospects = deduplicate_serp_results(serp_results, location=location)

            # Enrich
            if not skip_enrichment and prospects:
                config = ScraperConfig()

                async def enrich_all():
                    async with WebsiteCrawler(config) as crawler:
                        for prospect in prospects:
                            try:
                                await crawler.enrich_prospect(prospect)
                            except Exception:
                                pass

                asyncio.run(enrich_all())

            # Score
            for prospect in prospects:
                prospect.fit_score = calculate_fit_score(prospect)
                prospect.opportunity_score = calculate_opportunity_score(prospect)
                prospect.priority_score = (prospect.fit_score + prospect.opportunity_score) / 2
                prospect.opportunity_notes = generate_opportunity_notes(prospect)

            prospects.sort(key=lambda p: p.priority_score, reverse=True)

            # Export
            export_prospects(prospects, str(output_file), output_format)

            if not quiet:
                console.print(f"[green]✓[/green] {output_file} ({len(prospects)} prospects)")

            success_count += 1

        except Exception as e:
            console.print(f"[red]✗[/red] {business_type} in {location}: {e}")

    if not quiet:
        console.print(f"\n[green]Batch complete: {success_count}/{len(queries)} searches[/green]")

    sys.exit(0 if success_count == len(queries) else 1)


# ============================================================================
# Check Command
# ============================================================================

@cli.command()
def check():
    """Check configuration and API availability."""
    # SerpAPI
    serpapi_key = os.environ.get("SERPAPI_KEY", "")
    if serpapi_key:
        click.echo(f"✓ SERPAPI_KEY: {serpapi_key[:8]}...")
    else:
        click.echo("✗ SERPAPI_KEY: not set")

    # Google Sheets
    sheets_creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
    sheets_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS", "")
    if sheets_creds:
        click.echo(f"✓ Google Sheets: credentials file configured")
    elif sheets_json:
        click.echo(f"✓ Google Sheets: credentials JSON configured")
    else:
        click.echo("✗ Google Sheets: not configured")

    # Test SerpAPI connection
    if serpapi_key:
        try:
            client = SerpAPIClient()
            client.close()
            click.echo("✓ SerpAPI: connection OK")
        except Exception as e:
            click.echo(f"✗ SerpAPI: {e}")


# ============================================================================
# Version Command
# ============================================================================

@cli.command()
def version():
    """Show version info."""
    from prospect import __version__
    click.echo(f"prospect-scraper {__version__}")


# ============================================================================
# Web Command
# ============================================================================

@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to.")
@click.option("--port", default=8000, help="Port to bind to.")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development.")
def web(host: str, port: int, reload: bool) -> None:
    """Start the web interface."""
    import uvicorn

    console.print(
        Panel.fit(
            f"[bold]Prospect Scraper Web UI[/bold]\n"
            f"Running at: [cyan]http://{host}:{port}[/cyan]",
            border_style="blue",
        )
    )
    console.print("Press Ctrl+C to stop\n")

    uvicorn.run(
        "prospect.web.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ============================================================================
# Legacy Entry Point (for backward compatibility)
# ============================================================================

def main():
    """Legacy entry point - redirects to CLI group."""
    cli()


if __name__ == "__main__":
    cli()
