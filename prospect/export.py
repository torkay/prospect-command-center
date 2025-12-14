"""Export functionality for prospects (CSV, JSON)."""

import csv
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import Prospect

logger = logging.getLogger(__name__)


def export_to_csv(
    prospects: list[Prospect],
    output_path: str,
    include_signals: bool = True,
) -> str:
    """
    Export prospects to CSV file.

    Args:
        prospects: List of prospects to export
        output_path: Path to output file
        include_signals: Whether to include detailed signal columns

    Returns:
        Path to the created file
    """
    # Define columns
    base_columns = [
        "name",
        "website",
        "domain",
        "phone",
        "address",
        "emails",
        "rating",
        "review_count",
        "category",
        "found_in_ads",
        "ad_position",
        "found_in_maps",
        "maps_position",
        "found_in_organic",
        "organic_position",
        "fit_score",
        "opportunity_score",
        "priority_score",
        "opportunity_notes",
    ]

    signal_columns = [
        "site_reachable",
        "cms",
        "has_google_analytics",
        "has_facebook_pixel",
        "has_google_ads",
        "has_booking_system",
        "load_time_ms",
    ]

    columns = base_columns + signal_columns if include_signals else base_columns

    # Create output directory if needed
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()

        for prospect in prospects:
            row = {
                "name": prospect.name,
                "website": prospect.website or "",
                "domain": prospect.domain or "",
                "phone": prospect.phone or "",
                "address": prospect.address or "",
                "emails": "; ".join(prospect.emails) if prospect.emails else "",
                "rating": prospect.rating or "",
                "review_count": prospect.review_count or "",
                "category": prospect.category or "",
                "found_in_ads": "Yes" if prospect.found_in_ads else "No",
                "ad_position": prospect.ad_position or "",
                "found_in_maps": "Yes" if prospect.found_in_maps else "No",
                "maps_position": prospect.maps_position or "",
                "found_in_organic": "Yes" if prospect.found_in_organic else "No",
                "organic_position": prospect.organic_position or "",
                "fit_score": prospect.fit_score,
                "opportunity_score": prospect.opportunity_score,
                "priority_score": round(prospect.priority_score, 2),
                "opportunity_notes": prospect.opportunity_notes,
            }

            if include_signals and prospect.signals:
                row.update({
                    "site_reachable": "Yes" if prospect.signals.reachable else "No",
                    "cms": prospect.signals.cms or "",
                    "has_google_analytics": "Yes" if prospect.signals.has_google_analytics else "No",
                    "has_facebook_pixel": "Yes" if prospect.signals.has_facebook_pixel else "No",
                    "has_google_ads": "Yes" if prospect.signals.has_google_ads else "No",
                    "has_booking_system": "Yes" if prospect.signals.has_booking_system else "No",
                    "load_time_ms": prospect.signals.load_time_ms or "",
                })
            elif include_signals:
                row.update({
                    "site_reachable": "",
                    "cms": "",
                    "has_google_analytics": "",
                    "has_facebook_pixel": "",
                    "has_google_ads": "",
                    "has_booking_system": "",
                    "load_time_ms": "",
                })

            writer.writerow(row)

    logger.info("Exported %d prospects to %s", len(prospects), output_path)
    return str(output_path)


def export_to_json(
    prospects: list[Prospect],
    output_path: str,
    pretty: bool = True,
) -> str:
    """
    Export prospects to JSON file.

    Args:
        prospects: List of prospects to export
        output_path: Path to output file
        pretty: Whether to format JSON with indentation

    Returns:
        Path to the created file
    """
    # Create output directory if needed
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "exported_at": datetime.now().isoformat(),
        "total_prospects": len(prospects),
        "prospects": [prospect_to_dict(p) for p in prospects],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, indent=2, default=str)
        else:
            json.dump(data, f, default=str)

    logger.info("Exported %d prospects to %s", len(prospects), output_path)
    return str(output_path)


def prospect_to_dict(prospect: Prospect) -> dict:
    """
    Convert a Prospect to a dictionary for JSON serialization.

    Args:
        prospect: Prospect to convert

    Returns:
        Dictionary representation
    """
    data = {
        "name": prospect.name,
        "website": prospect.website,
        "domain": prospect.domain,
        "phone": prospect.phone,
        "address": prospect.address,
        "emails": prospect.emails,
        "serp_presence": {
            "ads": {
                "found": prospect.found_in_ads,
                "position": prospect.ad_position,
            },
            "maps": {
                "found": prospect.found_in_maps,
                "position": prospect.maps_position,
            },
            "organic": {
                "found": prospect.found_in_organic,
                "position": prospect.organic_position,
            },
        },
        "google_business": {
            "rating": prospect.rating,
            "review_count": prospect.review_count,
            "category": prospect.category,
        },
        "scores": {
            "fit": prospect.fit_score,
            "opportunity": prospect.opportunity_score,
            "priority": round(prospect.priority_score, 2),
        },
        "opportunity_notes": prospect.opportunity_notes,
        "source": prospect.source,
        "scraped_at": prospect.scraped_at.isoformat() if prospect.scraped_at else None,
    }

    if prospect.signals:
        data["signals"] = {
            "reachable": prospect.signals.reachable,
            "cms": prospect.signals.cms,
            "tracking": {
                "google_analytics": prospect.signals.has_google_analytics,
                "facebook_pixel": prospect.signals.has_facebook_pixel,
                "google_ads": prospect.signals.has_google_ads,
            },
            "has_booking_system": prospect.signals.has_booking_system,
            "load_time_ms": prospect.signals.load_time_ms,
            "title": prospect.signals.title,
            "meta_description": prospect.signals.meta_description,
            "social_links": prospect.signals.social_links,
        }

    return data


def export_prospects(
    prospects: list[Prospect],
    output_path: str,
    format: str = "csv",
) -> str:
    """
    Export prospects to file in specified format.

    Args:
        prospects: List of prospects to export
        output_path: Path to output file
        format: Output format ("csv" or "json")

    Returns:
        Path to the created file
    """
    if format.lower() == "json":
        return export_to_json(prospects, output_path)
    else:
        return export_to_csv(prospects, output_path)


def export_csv_string(prospects: list[Prospect]) -> str:
    """
    Export prospects to CSV string (for web download).

    Args:
        prospects: List of prospects to export

    Returns:
        CSV content as string
    """
    output = io.StringIO()

    fieldnames = [
        "name", "website", "phone", "address", "emails",
        "rating", "review_count", "fit_score", "opportunity_score",
        "priority_score", "opportunity_notes", "found_in_ads",
        "found_in_maps", "found_in_organic", "cms",
        "has_google_analytics", "has_booking_system"
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for p in prospects:
        # Get signals data if available
        signals = p.signals
        cms = signals.cms if signals else ""
        has_analytics = signals.has_google_analytics if signals else False
        has_booking = signals.has_booking_system if signals else False

        writer.writerow({
            "name": p.name or "",
            "website": p.website or "",
            "phone": p.phone or "",
            "address": p.address or "",
            "emails": "; ".join(p.emails) if p.emails else "",
            "rating": p.rating or "",
            "review_count": p.review_count or "",
            "fit_score": p.fit_score,
            "opportunity_score": p.opportunity_score,
            "priority_score": round(p.priority_score, 1),
            "opportunity_notes": p.opportunity_notes or "",
            "found_in_ads": "Yes" if p.found_in_ads else "No",
            "found_in_maps": "Yes" if p.found_in_maps else "No",
            "found_in_organic": "Yes" if p.found_in_organic else "No",
            "cms": cms or "",
            "has_google_analytics": "Yes" if has_analytics else "No",
            "has_booking_system": "Yes" if has_booking else "No",
        })

    return output.getvalue()
