"""
Prospect Scraper - Find businesses that need marketing help.

CLI Usage:
    prospect search "buyer's agent" "Brisbane" --limit 20
    prospect search "plumber" "Sydney" -f json -q | jq '.'

Library Usage:
    from prospect import search_prospects

    results = search_prospects(
        business_type="buyer's agent",
        location="Brisbane, QLD",
        limit=20,
        skip_enrichment=False
    )

    for r in results:
        print(f"{r.name}: {r.priority_score}")
"""

__version__ = "1.0.0"

from prospect.api import search_prospects, ProspectResult

__all__ = ["search_prospects", "ProspectResult", "__version__"]
