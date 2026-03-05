"""Google OAuth 2.0 authentication for rt CLI"""

import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required for the application
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/documents'
]

from rt.config import RT_DIR

TOKEN_FILE = RT_DIR / 'token.pickle'
CLIENT_SECRET_FILE = RT_DIR / 'client_secret.json'


def ensure_rt_directory():
    """Create ~/.rt directory if it doesn't exist"""
    RT_DIR.mkdir(exist_ok=True)


def get_credentials():
    """
    Get valid user credentials from storage or initiate OAuth flow.

    Returns:
        Credentials object for Google API access

    Raises:
        FileNotFoundError: If client_secret.json is not found
    """
    ensure_rt_directory()

    creds = None

    # Check if we have saved credentials
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired credentials
            creds.refresh(Request())
        else:
            # Check if client_secret.json exists
            if not CLIENT_SECRET_FILE.exists():
                raise FileNotFoundError(
                    f"Client secret file not found at {CLIENT_SECRET_FILE}\n\n"
                    "To set up authentication:\n"
                    "1. Go to https://console.cloud.google.com/\n"
                    "2. Create a new project or select existing one\n"
                    "3. Enable Google Drive API and Google Docs API\n"
                    "4. Create OAuth 2.0 credentials (Desktop app)\n"
                    "5. Download the client secret JSON file\n"
                    f"6. Save it as {CLIENT_SECRET_FILE}"
                )

            # Run OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def get_drive_service():
    """
    Build and return Google Drive API service

    Returns:
        Google Drive API service object
    """
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)


def get_docs_service():
    """
    Build and return Google Docs API service

    Returns:
        Google Docs API service object
    """
    creds = get_credentials()
    return build('docs', 'v1', credentials=creds)
