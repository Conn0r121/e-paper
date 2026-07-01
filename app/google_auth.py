"""One-time helper to mint a Google refresh token for the dashboard.

Run this ONCE, locally (not on the Pi). It opens a browser, you consent, and it
prints the three secrets to put in your Pi/Portainer environment:
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

Prerequisites:
  1. In Google Cloud console, enable the Calendar API and Tasks API, configure
     the OAuth consent screen, and create an OAuth client of type "Desktop app".
  2. Download that client's JSON and save it next to this script as
     client_secret.json (git-ignored).
  3. pip install -r requirements-auth.txt
  4. python app/google_auth.py

Read-only scopes only — the dashboard can never modify your calendar or tasks.
"""

import glob
import os
import sys

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("Missing deps. Run: pip install -r requirements-auth.txt")

    here = os.path.dirname(os.path.abspath(__file__))
    matches = sorted(glob.glob(os.path.join(here, "client_secret*.json")))
    if not matches:
        sys.exit("No client_secret*.json found next to google_auth.py. "
                 "Download your OAuth 'Desktop app' client JSON and save it here.")
    secrets_file = matches[0]
    print(f"Using {os.path.basename(secrets_file)}")

    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh token is issued.
    creds = flow.run_local_server(port=0, access_type="offline",
                                  prompt="consent")

    if not creds.refresh_token:
        sys.exit("No refresh token returned. Revoke prior access at "
                 "https://myaccount.google.com/permissions and retry.")

    print("\n=== Set these as environment variables (Pi / Portainer) ===\n")
    print(f"GOOGLE_CLIENT_ID={creds.client_id}")
    print(f"GOOGLE_CLIENT_SECRET={creds.client_secret}")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print("\nKeep these secret. Do not commit them.")


if __name__ == "__main__":
    main()
