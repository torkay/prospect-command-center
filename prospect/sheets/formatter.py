"""Google Sheets formatting utilities."""

from typing import Any

from prospect.models import Prospect

# Color definitions (RGB 0-1 scale for Google Sheets API)
COLORS = {
    "header_bg": {"red": 0.17, "green": 0.32, "blue": 0.51},  # Dark blue
    "header_fg": {"red": 1.0, "green": 1.0, "blue": 1.0},     # White
    "high_score": {"red": 0.78, "green": 0.92, "blue": 0.78}, # Light green
    "medium_score": {"red": 1.0, "green": 0.95, "blue": 0.8}, # Light yellow
    "low_score": {"red": 0.96, "green": 0.8, "blue": 0.8},    # Light red
    "alt_row": {"red": 0.95, "green": 0.95, "blue": 0.95},    # Light gray
}

# Column configurations
COLUMNS = [
    {"name": "Name", "width": 200},
    {"name": "Website", "width": 250},
    {"name": "Phone", "width": 120},
    {"name": "Address", "width": 200},
    {"name": "Emails", "width": 200},
    {"name": "Rating", "width": 60},
    {"name": "Reviews", "width": 70},
    {"name": "Fit Score", "width": 80},
    {"name": "Opportunity", "width": 90},
    {"name": "Priority", "width": 70},
    {"name": "Opportunity Notes", "width": 350},
    {"name": "In Ads", "width": 60},
    {"name": "In Maps", "width": 60},
    {"name": "In Organic", "width": 70},
    {"name": "CMS", "width": 100},
    {"name": "Has Analytics", "width": 90},
    {"name": "Has Booking", "width": 90},
]


def get_header_row() -> list[str]:
    """Get column headers."""
    return [col["name"] for col in COLUMNS]


def get_column_widths() -> list[int]:
    """Get column widths in pixels."""
    return [col["width"] for col in COLUMNS]


def prospect_to_row(prospect: Prospect) -> list[Any]:
    """
    Convert a Prospect to a spreadsheet row.

    Args:
        prospect: Prospect object

    Returns:
        List of cell values
    """
    # Extract signals data if available
    signals = prospect.signals
    cms = signals.cms if signals else None
    has_analytics = signals.has_google_analytics if signals else False
    has_booking = signals.has_booking_system if signals else False

    return [
        prospect.name or "",
        prospect.website or "",
        prospect.phone or "",
        prospect.address or "",
        "; ".join(prospect.emails) if prospect.emails else "",
        prospect.rating or "",
        prospect.review_count or "",
        prospect.fit_score,
        prospect.opportunity_score,
        round(prospect.priority_score, 1),
        prospect.opportunity_notes or "",
        "Yes" if prospect.found_in_ads else "No",
        "Yes" if prospect.found_in_maps else "No",
        "Yes" if prospect.found_in_organic else "No",
        cms or "",
        "Yes" if has_analytics else "No",
        "Yes" if has_booking else "No",
    ]


def get_score_color(score: float) -> dict:
    """
    Get background color based on score.

    Args:
        score: Score value (0-100 or priority 0-100)

    Returns:
        RGB color dict for Google Sheets API
    """
    if score >= 60:
        return COLORS["high_score"]
    elif score >= 40:
        return COLORS["medium_score"]
    else:
        return COLORS["low_score"]


def build_header_format_request(sheet_id: int) -> dict:
    """Build API request for header row formatting."""
    return {
        "repeatCell": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 1,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": COLORS["header_bg"],
                    "textFormat": {
                        "foregroundColor": COLORS["header_fg"],
                        "bold": True,
                        "fontSize": 10,
                    },
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment)",
        }
    }


def build_column_width_requests(sheet_id: int) -> list[dict]:
    """Build API requests for column widths."""
    requests = []
    for i, width in enumerate(get_column_widths()):
        requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": width},
                "fields": "pixelSize",
            }
        })
    return requests


def build_score_color_requests(sheet_id: int, num_rows: int, score_columns: list[int]) -> list[dict]:
    """
    Build API requests for score-based conditional formatting.

    Args:
        sheet_id: Google Sheet ID
        num_rows: Number of data rows
        score_columns: Column indices to apply score coloring (0-indexed)
    """
    requests = []

    # Add conditional formatting rules for each score column
    for col_idx in score_columns:
        # High score (green) - >= 60
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,  # Skip header
                        "endRowIndex": num_rows + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_GREATER_THAN_EQ",
                            "values": [{"userEnteredValue": "60"}]
                        },
                        "format": {"backgroundColor": COLORS["high_score"]}
                    }
                },
                "index": 0
            }
        })

        # Medium score (yellow) - 40-59
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": num_rows + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_BETWEEN",
                            "values": [
                                {"userEnteredValue": "40"},
                                {"userEnteredValue": "59"}
                            ]
                        },
                        "format": {"backgroundColor": COLORS["medium_score"]}
                    }
                },
                "index": 1
            }
        })

        # Low score (red) - < 40
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": num_rows + 1,
                        "startColumnIndex": col_idx,
                        "endColumnIndex": col_idx + 1,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "NUMBER_LESS",
                            "values": [{"userEnteredValue": "40"}]
                        },
                        "format": {"backgroundColor": COLORS["low_score"]}
                    }
                },
                "index": 2
            }
        })

    return requests


def build_freeze_header_request(sheet_id: int) -> dict:
    """Build API request to freeze header row."""
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 1}
            },
            "fields": "gridProperties.frozenRowCount"
        }
    }
