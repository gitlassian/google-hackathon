"""One-time channel connect: opens a browser, stores a refresh token.

    python connect_youtube.py           # connect (or reconnect) the default channel
    python connect_youtube.py --status  # show who is connected
    python connect_youtube.py --forget  # drop the stored token

Run from the backend/ directory.
"""

from __future__ import annotations

import argparse
import sys

from googleapiclient.discovery import build

from app.youtube.auth import DEFAULT_KEY, FileCredentialStore, load_credentials, run_installed_app_flow
from app.youtube.errors import NotAuthenticated


def show_channel(credentials) -> None:
    youtube = build("youtube", "v3", credentials=credentials)
    items = youtube.channels().list(part="snippet,statistics", mine=True).execute().get("items", [])
    if not items:
        print("Connected, but this account owns no channel.")
        return
    snippet, stats = items[0]["snippet"], items[0]["statistics"]
    print(f"Connected as {snippet['title']} ({items[0]['id']})")
    print(f"  {stats.get('videoCount', '?')} videos, {stats.get('subscriberCount', '?')} subscribers")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true", help="report the stored credentials")
    parser.add_argument("--forget", action="store_true", help="delete the stored credentials")
    args = parser.parse_args()

    store = FileCredentialStore()

    if args.forget:
        store.delete(DEFAULT_KEY)
        print(f"Removed stored credentials from {store.path}")
        return 0

    if args.status:
        try:
            show_channel(load_credentials(store))
        except NotAuthenticated as exc:
            print(f"Not connected: {exc}")
            return 1
        return 0

    show_channel(run_installed_app_flow(store))
    print(f"Refresh token cached in {store.path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
