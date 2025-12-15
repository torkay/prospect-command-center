"""Google Sheets authentication handling."""

import os
import json
import logging
from pathlib import Path
from typing import Optional

from google.oauth2.service_account import Credentials
import gspread

logger = logging.getLogger(__name__)

# Required scopes for Sheets API
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
]

# Default credential locations
DEFAULT_CRED_PATHS = [
    # New naming
    Path.home() / ".config" / "prospect-command-center" / "credentials.json",
    Path.home() / ".prospect-command-center-credentials.json",
    # Backward compatibility
    Path.home() / ".config" / "prospect-scraper" / "credentials.json",
    Path.home() / ".prospect-scraper-credentials.json",
    Path("credentials.json"),
]


class AuthenticationError(Exception):
    """Failed to authenticate with Google Sheets API."""
    pass


def get_credentials() -> Credentials:
    """
    Load Google service account credentials.

    Checks in order:
    1. GOOGLE_SHEETS_CREDENTIALS env var (JSON string)
    2. GOOGLE_SHEETS_CREDENTIALS_FILE env var (path to JSON file)
    3. Default file locations

    Returns:
        Credentials object for Google API

    Raises:
        AuthenticationError: If no valid credentials found
    """
    # Try environment variable (JSON string)
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    if creds_json:
        try:
            creds_data = json.loads(creds_json)
            return Credentials.from_service_account_info(creds_data, scopes=SCOPES)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in GOOGLE_SHEETS_CREDENTIALS: {e}")

    # Try environment variable (file path)
    creds_file = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE")
    if creds_file:
        path = Path(creds_file)
        if path.exists():
            return Credentials.from_service_account_file(str(path), scopes=SCOPES)
        else:
            logger.warning(f"Credentials file not found: {creds_file}")

    # Try default locations
    for path in DEFAULT_CRED_PATHS:
        if path.exists():
            logger.info(f"Using credentials from {path}")
            return Credentials.from_service_account_file(str(path), scopes=SCOPES)

    # No credentials found
    raise AuthenticationError(
        "Google Sheets credentials not found.\n\n"
        "To set up Google Sheets export:\n"
        "1. Go to https://console.cloud.google.com/\n"
        "2. Create a project and enable the Google Sheets API\n"
        "3. Create a service account (APIs & Services > Credentials)\n"
        "4. Download the JSON key file\n"
        "5. Either:\n"
        "   a. Set GOOGLE_SHEETS_CREDENTIALS_FILE=/path/to/credentials.json\n"
        "   b. Place credentials.json in ~/.config/prospect-command-center/ (or ~/.config/prospect-scraper/)\n"
        "   c. Set GOOGLE_SHEETS_CREDENTIALS to the JSON content\n"
    )


def get_client() -> gspread.Client:
    """
    Get authenticated gspread client.

    Returns:
        Authenticated gspread.Client

    Raises:
        AuthenticationError: If authentication fails
    """
    credentials = get_credentials()
    return gspread.authorize(credentials)
