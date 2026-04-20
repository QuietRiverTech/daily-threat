#!/usr/bin/env python3
"""
auth_setup.py — One-time OAuth2 setup for The Daily Threat YouTube uploads.

Run this once:
    python auth_setup.py

It will open your browser for Google OAuth2 consent. Grant YouTube upload
permission, and the refresh token is saved to token.json for future automatic use.
"""

import sys
from pathlib import Path

# Ensure we can import from this directory
sys.path.insert(0, str(Path(__file__).parent))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

BASE_DIR = Path(__file__).parent
CLIENT_SECRET_FILE = BASE_DIR / "client_secret.json"
TOKEN_FILE = BASE_DIR / "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    print("=" * 50)
    print("  The Daily Threat — YouTube OAuth2 Setup")
    print("=" * 50)
    print()

    if not CLIENT_SECRET_FILE.exists():
        print(f"ERROR: client_secret.json not found at:")
        print(f"  {CLIENT_SECRET_FILE}")
        print()
        print("Download it from Google Cloud Console:")
        print("  1. Go to https://console.cloud.google.com/apis/credentials")
        print("  2. Create OAuth2 client (Desktop app)")
        print("  3. Download JSON and save as client_secret.json")
        sys.exit(1)

    # Check if we already have a valid token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.valid:
            print("✓ token.json already exists and is valid!")
            print("  You're all set for automatic uploads.")
            return
        elif creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            print("✓ Token refreshed successfully!")
            return

    print("Starting OAuth2 consent flow...")
    print()
    print("Waiting for authorization...")
    print("A URL will appear below — open it in your browser.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE), SCOPES
    )
    # Bind to all interfaces but redirect back to localhost
    # User must access via http://localhost:8080 OR the flow handles the redirect
    creds = flow.run_local_server(
        host="localhost",
        port=9090,
        prompt="consent",
        open_browser=False,
        success_message="Authorization complete! You can close this tab.",
    )

    # Save the token
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

    print()
    print("✓ Authentication successful!")
    print(f"  Token saved to: {TOKEN_FILE}")
    print()
    print("You can now run uploads automatically without browser interaction.")
    print("The token will auto-refresh as needed.")


if __name__ == "__main__":
    main()
