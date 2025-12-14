"""Tests for Google Sheets export."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from prospect.sheets.auth import get_credentials, AuthenticationError, DEFAULT_CRED_PATHS
from prospect.sheets.formatter import (
    get_header_row,
    prospect_to_row,
    get_score_color,
    COLORS,
)
from prospect.sheets.client import SheetsExporter, SheetsError
from prospect.models import Prospect, WebsiteSignals


class TestFormatter:
    """Test formatting utilities."""

    def test_get_header_row(self):
        """Headers should include all expected columns."""
        headers = get_header_row()

        assert "Name" in headers
        assert "Website" in headers
        assert "Fit Score" in headers
        assert "Opportunity" in headers
        assert "Opportunity Notes" in headers

    def test_header_row_has_17_columns(self):
        """Should have exactly 17 columns."""
        headers = get_header_row()
        assert len(headers) == 17

    def test_prospect_to_row(self):
        """Prospect should convert to correct row format."""
        # Create signals
        signals = WebsiteSignals(
            url="https://test.com",
            reachable=True,
            cms="WordPress",
            has_google_analytics=True,
            has_booking_system=False,
        )

        # Create prospect
        prospect = Prospect(
            name="Test Business",
            website="https://test.com",
            phone="0400 000 000",
            address="123 Test St",
            emails=["info@test.com"],
            rating=4.5,
            review_count=50,
            fit_score=75,
            opportunity_score=60,
            priority_score=66.0,
            opportunity_notes="No booking system",
            found_in_ads=True,
            found_in_maps=True,
            found_in_organic=False,
            signals=signals,
        )

        row = prospect_to_row(prospect)

        assert row[0] == "Test Business"
        assert row[1] == "https://test.com"
        assert row[2] == "0400 000 000"
        assert row[3] == "123 Test St"
        assert row[4] == "info@test.com"
        assert row[5] == 4.5
        assert row[6] == 50
        assert row[7] == 75  # Fit score
        assert row[8] == 60  # Opportunity score
        assert row[9] == 66.0  # Priority score
        assert row[10] == "No booking system"
        assert row[11] == "Yes"  # In ads
        assert row[12] == "Yes"  # In maps
        assert row[13] == "No"  # In organic
        assert row[14] == "WordPress"  # CMS
        assert row[15] == "Yes"  # Has analytics
        assert row[16] == "No"  # Has booking

    def test_prospect_to_row_without_signals(self):
        """Prospect without signals should still convert correctly."""
        prospect = Prospect(
            name="Simple Business",
            website="https://simple.com",
            fit_score=50,
            opportunity_score=40,
            priority_score=45.0,
        )

        row = prospect_to_row(prospect)

        assert row[0] == "Simple Business"
        assert row[14] == ""  # CMS should be empty
        assert row[15] == "No"  # Has analytics
        assert row[16] == "No"  # Has booking

    def test_prospect_to_row_with_multiple_emails(self):
        """Multiple emails should be joined with semicolons."""
        prospect = Prospect(
            name="Multi Email",
            emails=["a@test.com", "b@test.com", "c@test.com"],
            fit_score=50,
            opportunity_score=50,
            priority_score=50.0,
        )

        row = prospect_to_row(prospect)

        assert row[4] == "a@test.com; b@test.com; c@test.com"

    def test_score_colors(self):
        """Score colors should match thresholds."""
        assert get_score_color(80) == COLORS["high_score"]
        assert get_score_color(60) == COLORS["high_score"]
        assert get_score_color(50) == COLORS["medium_score"]
        assert get_score_color(40) == COLORS["medium_score"]
        assert get_score_color(39) == COLORS["low_score"]
        assert get_score_color(30) == COLORS["low_score"]
        assert get_score_color(0) == COLORS["low_score"]

    def test_score_color_boundaries(self):
        """Test exact boundary values."""
        assert get_score_color(59) == COLORS["medium_score"]
        assert get_score_color(60) == COLORS["high_score"]
        assert get_score_color(39) == COLORS["low_score"]
        assert get_score_color(40) == COLORS["medium_score"]


class TestAuthentication:
    """Test credential handling."""

    def test_missing_credentials_raises_error(self, monkeypatch, tmp_path):
        """Should raise AuthenticationError when no credentials found."""
        # Clear environment
        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS_FILE", raising=False)

        # Patch default paths to non-existent locations
        monkeypatch.setattr(
            "prospect.sheets.auth.DEFAULT_CRED_PATHS",
            [tmp_path / "nonexistent.json"]
        )

        with pytest.raises(AuthenticationError) as exc_info:
            get_credentials()

        assert "credentials not found" in str(exc_info.value).lower()

    def test_error_message_includes_setup_instructions(self, monkeypatch, tmp_path):
        """Error should include helpful setup instructions."""
        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS_FILE", raising=False)
        monkeypatch.setattr(
            "prospect.sheets.auth.DEFAULT_CRED_PATHS",
            [tmp_path / "nonexistent.json"]
        )

        with pytest.raises(AuthenticationError) as exc_info:
            get_credentials()

        error_msg = str(exc_info.value)
        assert "console.cloud.google.com" in error_msg
        assert "service account" in error_msg.lower()

    def test_env_file_path_not_found_logs_warning(self, monkeypatch, tmp_path, caplog):
        """Should log warning when file path doesn't exist."""
        import logging
        caplog.set_level(logging.WARNING)

        monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS", raising=False)
        monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS_FILE", "/nonexistent/path.json")
        monkeypatch.setattr(
            "prospect.sheets.auth.DEFAULT_CRED_PATHS",
            [tmp_path / "nonexistent.json"]
        )

        with pytest.raises(AuthenticationError):
            get_credentials()

        assert "not found" in caplog.text.lower()


class TestSheetsExporter:
    """Test SheetsExporter functionality."""

    def test_export_empty_list_raises_error(self):
        """Should raise error when exporting empty list."""
        with patch('prospect.sheets.client.get_client'):
            exporter = SheetsExporter()

            with pytest.raises(SheetsError) as exc_info:
                exporter.export([])

            assert "No prospects" in str(exc_info.value)

    def test_append_empty_list_raises_error(self):
        """Should raise error when appending empty list."""
        with patch('prospect.sheets.client.get_client'):
            exporter = SheetsExporter()

            with pytest.raises(SheetsError) as exc_info:
                exporter.append([], sheet_id="abc123")

            assert "No prospects" in str(exc_info.value)

    @patch('prospect.sheets.client.get_client')
    def test_export_creates_spreadsheet(self, mock_get_client):
        """Should create spreadsheet and return URL."""
        # Setup mocks
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_worksheet = Mock()

        mock_spreadsheet.url = "https://docs.google.com/spreadsheets/d/abc123"
        mock_spreadsheet.sheet1 = mock_worksheet
        mock_worksheet._properties = {'sheetId': 0}

        mock_client.create.return_value = mock_spreadsheet
        mock_get_client.return_value = mock_client

        # Create prospect
        prospect = Prospect(
            name="Test",
            website="https://test.com",
            fit_score=50,
            opportunity_score=50,
            priority_score=50.0,
            found_in_organic=True,
        )

        # Export
        exporter = SheetsExporter()
        url = exporter.export([prospect], name="Test Sheet")

        # Verify
        assert url == "https://docs.google.com/spreadsheets/d/abc123"
        mock_client.create.assert_called_once_with("Test Sheet")

    @patch('prospect.sheets.client.get_client')
    def test_export_auto_generates_name(self, mock_get_client):
        """Should auto-generate sheet name when not provided."""
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_worksheet = Mock()

        mock_spreadsheet.url = "https://docs.google.com/spreadsheets/d/xyz"
        mock_spreadsheet.sheet1 = mock_worksheet
        mock_worksheet._properties = {'sheetId': 0}

        mock_client.create.return_value = mock_spreadsheet
        mock_get_client.return_value = mock_client

        prospect = Prospect(name="Test", fit_score=50, opportunity_score=50, priority_score=50.0)

        exporter = SheetsExporter()
        exporter.export([prospect])  # No name provided

        # Verify create was called with auto-generated name
        call_args = mock_client.create.call_args[0][0]
        assert "Prospects" in call_args

    @patch('prospect.sheets.client.get_client')
    def test_export_shares_with_users(self, mock_get_client):
        """Should share with provided email addresses."""
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_worksheet = Mock()

        mock_spreadsheet.url = "https://docs.google.com/spreadsheets/d/xyz"
        mock_spreadsheet.sheet1 = mock_worksheet
        mock_worksheet._properties = {'sheetId': 0}

        mock_client.create.return_value = mock_spreadsheet
        mock_get_client.return_value = mock_client

        prospect = Prospect(name="Test", fit_score=50, opportunity_score=50, priority_score=50.0)

        exporter = SheetsExporter()
        exporter.export([prospect], share_with=["user1@example.com", "user2@example.com"])

        # Verify share was called for each email
        share_calls = [call for call in mock_spreadsheet.share.call_args_list
                      if call[0][0] in ["user1@example.com", "user2@example.com"]]
        assert len(share_calls) == 2

    @patch('prospect.sheets.client.get_client')
    def test_append_finds_next_row(self, mock_get_client):
        """Should append data starting at the next empty row."""
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_worksheet = Mock()

        mock_spreadsheet.url = "https://docs.google.com/spreadsheets/d/abc"
        # Simulate sheet with header + 5 existing rows
        mock_worksheet.get_all_values.return_value = [
            ["Header1", "Header2"],
            ["Row1"],
            ["Row2"],
            ["Row3"],
            ["Row4"],
            ["Row5"],
        ]
        mock_worksheet._properties = {'sheetId': 0}

        mock_client.open_by_key.return_value = mock_spreadsheet
        mock_spreadsheet.worksheet.return_value = mock_worksheet
        mock_get_client.return_value = mock_client

        prospect = Prospect(name="New", fit_score=50, opportunity_score=50, priority_score=50.0)

        exporter = SheetsExporter()
        exporter.append([prospect], sheet_id="existing_id")

        # Should update starting at row 7 (6 existing + 1)
        mock_worksheet.update.assert_called_once()
        call_args = mock_worksheet.update.call_args[0]
        assert call_args[0] == "A7"


class TestExceptionHierarchy:
    """Test exception class relationships."""

    def test_sheets_error_is_exception(self):
        """SheetsError should be an Exception."""
        assert issubclass(SheetsError, Exception)

    def test_authentication_error_is_exception(self):
        """AuthenticationError should be an Exception."""
        assert issubclass(AuthenticationError, Exception)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("GOOGLE_SHEETS_CREDENTIALS") and
    not os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE"),
    reason="Google Sheets credentials required"
)
class TestSheetsIntegration:
    """Live integration tests (require credentials)."""

    def test_create_and_write_sheet(self):
        """Test creating a real spreadsheet."""
        from prospect.sheets import SheetsExporter
        from prospect.models import Prospect, WebsiteSignals

        signals = WebsiteSignals(
            url="https://test.com",
            reachable=True,
            cms="WordPress",
            has_google_analytics=True,
            has_booking_system=False,
        )

        prospect = Prospect(
            name="Integration Test Business",
            website="https://test.com",
            phone="0400 000 000",
            address="123 Test St, Sydney",
            emails=["test@example.com"],
            rating=4.5,
            review_count=25,
            fit_score=70,
            opportunity_score=55,
            priority_score=61.0,
            opportunity_notes="Test prospect",
            found_in_ads=False,
            found_in_maps=True,
            found_in_organic=True,
            signals=signals,
        )

        exporter = SheetsExporter()
        url = exporter.export([prospect], name="Prospect Scraper Test")

        assert "docs.google.com/spreadsheets" in url
        print(f"\nCreated test sheet: {url}")
