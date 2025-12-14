"""Google Sheets export client."""

import logging
from datetime import datetime
from typing import Optional

import gspread
from gspread.exceptions import SpreadsheetNotFound, APIError

from prospect.sheets.auth import get_client, AuthenticationError
from prospect.sheets.formatter import (
    get_header_row,
    prospect_to_row,
    build_header_format_request,
    build_column_width_requests,
    build_score_color_requests,
    build_freeze_header_request,
)
from prospect.models import Prospect

logger = logging.getLogger(__name__)


class SheetsError(Exception):
    """Google Sheets operation failed."""
    pass


class SheetsExporter:
    """
    Export prospects to Google Sheets.

    Usage:
        exporter = SheetsExporter()
        url = exporter.export(prospects, name="My Prospects")

        # Or append to existing:
        url = exporter.append(prospects, sheet_id="1abc...")
    """

    def __init__(self):
        """Initialize the exporter with authenticated client."""
        try:
            self.client = get_client()
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError(f"Failed to initialize Google Sheets client: {e}")

    def export(
        self,
        prospects: list[Prospect],
        name: Optional[str] = None,
        share_with: Optional[list[str]] = None,
    ) -> str:
        """
        Export prospects to a new Google Sheet.

        Args:
            prospects: List of Prospect objects
            name: Sheet name (default: auto-generated with timestamp)
            share_with: List of email addresses to share with (optional)

        Returns:
            URL of the created spreadsheet
        """
        if not prospects:
            raise SheetsError("No prospects to export")

        # Generate name if not provided
        if not name:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            name = f"Prospects {timestamp}"

        logger.info(f"Creating new spreadsheet: {name}")

        try:
            # Create spreadsheet
            spreadsheet = self.client.create(name)
            worksheet = spreadsheet.sheet1
            worksheet.update_title("Prospects")

            # Write data
            self._write_data(worksheet, prospects)

            # Apply formatting
            self._apply_formatting(spreadsheet, worksheet, len(prospects))

            # Share if requested
            if share_with:
                for email in share_with:
                    try:
                        spreadsheet.share(email, perm_type='user', role='writer')
                        logger.info(f"Shared with {email}")
                    except Exception as e:
                        logger.warning(f"Failed to share with {email}: {e}")

            # Make link-shareable (anyone with link can view)
            try:
                spreadsheet.share('', perm_type='anyone', role='reader')
            except Exception as e:
                logger.warning(f"Could not enable link sharing: {e}")

            return spreadsheet.url

        except APIError as e:
            raise SheetsError(f"Google Sheets API error: {e}")
        except Exception as e:
            raise SheetsError(f"Failed to create spreadsheet: {e}")

    def append(
        self,
        prospects: list[Prospect],
        sheet_id: str,
        worksheet_name: str = "Prospects",
    ) -> str:
        """
        Append prospects to an existing Google Sheet.

        Args:
            prospects: List of Prospect objects
            sheet_id: ID of existing spreadsheet (from URL)
            worksheet_name: Name of worksheet to append to

        Returns:
            URL of the spreadsheet
        """
        if not prospects:
            raise SheetsError("No prospects to export")

        logger.info(f"Appending to spreadsheet: {sheet_id}")

        try:
            spreadsheet = self.client.open_by_key(sheet_id)

            # Get or create worksheet
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(worksheet_name, rows=1000, cols=20)
                # Write headers for new worksheet
                worksheet.update('A1', [get_header_row()])

            # Find first empty row
            all_values = worksheet.get_all_values()
            next_row = len(all_values) + 1

            # If sheet is empty, add headers first
            if next_row == 1:
                worksheet.update('A1', [get_header_row()])
                next_row = 2

            # Prepare data rows
            rows = [prospect_to_row(p) for p in prospects]

            # Append data
            worksheet.update(f'A{next_row}', rows)

            logger.info(f"Appended {len(prospects)} prospects starting at row {next_row}")

            return spreadsheet.url

        except SpreadsheetNotFound:
            raise SheetsError(
                f"Spreadsheet not found: {sheet_id}\n"
                "Make sure the service account has access to this spreadsheet."
            )
        except APIError as e:
            raise SheetsError(f"Google Sheets API error: {e}")
        except Exception as e:
            raise SheetsError(f"Failed to append to spreadsheet: {e}")

    def _write_data(self, worksheet, prospects: list[Prospect]) -> None:
        """Write header and data rows to worksheet."""
        # Prepare all data
        header = get_header_row()
        rows = [prospect_to_row(p) for p in prospects]
        all_data = [header] + rows

        # Write in one batch (much faster than row-by-row)
        worksheet.update('A1', all_data)

        logger.info(f"Wrote {len(prospects)} prospects to sheet")

    def _apply_formatting(self, spreadsheet, worksheet, num_rows: int) -> None:
        """Apply formatting to the worksheet."""
        sheet_id = worksheet._properties['sheetId']

        # Build formatting requests
        requests = []

        # Header formatting
        requests.append(build_header_format_request(sheet_id))

        # Column widths
        requests.extend(build_column_width_requests(sheet_id))

        # Freeze header row
        requests.append(build_freeze_header_request(sheet_id))

        # Score coloring (columns: Fit Score=7, Opportunity=8, Priority=9, 0-indexed)
        requests.extend(build_score_color_requests(sheet_id, num_rows, [7, 8, 9]))

        # Execute all formatting in one batch
        if requests:
            spreadsheet.batch_update({"requests": requests})

        logger.info("Applied formatting")
