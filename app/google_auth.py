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

    values = {
        "GOOGLE_CLIENT_ID": creds.client_id,
        "GOOGLE_CLIENT_SECRET": creds.client_secret,
        "GOOGLE_REFRESH_TOKEN": creds.refresh_token,
    }

    # Write to a git-ignored file so you never have to copy from the terminal.
    repo_root = os.path.dirname(here)
    out_path = os.path.join(repo_root, "google_creds.env")
    with open(out_path, "w", encoding="utf-8") as f:
        for key, val in values.items():
            f.write(f"{key}={val}\n")
    print(f"\nSaved credentials to: {out_path}")
    print("Open that file (git-ignored) and paste the 3 lines into Portainer.\n")

    _self_test(values)


def _self_test(values):
    """Immediately verify the new credentials against Google, no copy needed."""
    for key, val in values.items():
        os.environ[key] = val

    import google_sync  # imported after env is set so config picks it up

    print("Testing Google connection...")
    events = google_sync.fetch_events()
    tasks = google_sync.fetch_tasks()

    print(f"\n  Calendar events today: {len(events)}")
    for e in events[:5]:
        print(f"    {e.time_label:>9}  {e.title}")
    print(f"\n  Open tasks: {len(tasks)}")
    for t in tasks[:5]:
        print(f"    [ ] {t.title}")

    if events or tasks:
        print("\n✓ Google is working. Paste google_creds.env into Portainer to "
              "deploy.")
    else:
        print("\nConnected, but nothing came back — you may just have no events/"
              "tasks today. Try adding a test event and re-running.")


if __name__ == "__main__":
    main()
