"""OAuth 2.0 credentials for the YouTube Data and Analytics APIs.

Two flows share one credential store:

* **CLI** - ``run_installed_app_flow()`` opens a browser once and caches a refresh
  token. This is what the probe script and local development use.
* **Web** - ``build_web_flow()`` / ``finish_web_flow()`` back the
  ``/youtube/auth/start`` and ``/youtube/auth/callback`` routes so a visitor can
  connect their own channel.

Setup (one time, https://console.cloud.google.com):
  1. Enable "YouTube Data API v3" and "YouTube Analytics API".
  2. Create an OAuth client ID. Type "Desktop app" for the CLI flow, "Web
     application" for the web flow (with YOUTUBE_OAUTH_REDIRECT_URI registered).
  3. Download the JSON to backend/client_secret.json.
  4. On the OAuth consent screen, add your Google account under "Test users".
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow

from .config import (
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_OAUTH_REDIRECT_URI,
    YOUTUBE_TOKEN_FILE,
)
from .errors import NotAuthenticated

# youtube.readonly     -> video and channel metadata for the authenticated channel
# yt-analytics.readonly -> reports.query, including audience retention
# Deliberately NOT requesting yt-analytics-monetary.readonly: we want no revenue
# data, and a smaller consent screen.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

DEFAULT_KEY = "default"


class CredentialStore(Protocol):
    """Where refresh tokens live. Swappable so the web flow can key by session."""

    def load(self, key: str) -> Credentials | None: ...

    def save(self, key: str, credentials: Credentials) -> None: ...

    def delete(self, key: str) -> None: ...


class FileCredentialStore:
    """Refresh tokens in a local JSON file, keyed by user. Good enough for one creator."""

    def __init__(self, path: Path | str = YOUTUBE_TOKEN_FILE) -> None:
        self.path = Path(path)

    def _read_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_all(self, data: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)  # no-op on Windows, meaningful everywhere else
        except OSError:
            pass

    def load(self, key: str = DEFAULT_KEY) -> Credentials | None:
        info = self._read_all().get(key)
        if not info:
            return None
        return Credentials.from_authorized_user_info(info, SCOPES)

    def save(self, key: str, credentials: Credentials) -> None:
        data = self._read_all()
        data[key] = json.loads(credentials.to_json())
        self._write_all(data)

    def delete(self, key: str) -> None:
        data = self._read_all()
        if data.pop(key, None) is not None:
            self._write_all(data)


class MemoryCredentialStore:
    """In-process store for the web flow. Tokens vanish on restart, which is fine."""

    def __init__(self) -> None:
        self._creds: dict[str, Credentials] = {}

    def load(self, key: str) -> Credentials | None:
        return self._creds.get(key)

    def save(self, key: str, credentials: Credentials) -> None:
        self._creds[key] = credentials

    def delete(self, key: str) -> None:
        self._creds.pop(key, None)


def _relax_scope_check() -> None:
    """Google often returns the granted scopes reordered, or adds 'openid'.

    oauthlib treats that as a fatal scope change. Relaxing it is the standard
    workaround and avoids the flow blowing up halfway through a demo.
    """
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


def _require_client_secrets() -> Path:
    path = Path(YOUTUBE_CLIENT_SECRETS_FILE)
    if not path.exists():
        raise NotAuthenticated(
            f"OAuth client secrets not found at {path}. Download the OAuth client JSON "
            "from https://console.cloud.google.com/apis/credentials, or point "
            "YOUTUBE_CLIENT_SECRETS_FILE at it."
        )
    return path


def load_credentials(
    store: CredentialStore | None = None, key: str = DEFAULT_KEY
) -> Credentials:
    """Return usable credentials, refreshing them if they have expired.

    Raises NotAuthenticated when the channel has never been connected.
    """
    store = store or FileCredentialStore()
    credentials = store.load(key)
    if credentials is None:
        raise NotAuthenticated(
            "No YouTube credentials stored. Run `python connect_youtube.py` to connect "
            "a channel, or use the /youtube/auth/start endpoint."
        )
    if credentials.valid:
        return credentials
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        store.save(key, credentials)
        return credentials
    raise NotAuthenticated("Stored YouTube credentials are unusable; reconnect the channel.")


def run_installed_app_flow(
    store: CredentialStore | None = None, key: str = DEFAULT_KEY, port: int = 0
) -> Credentials:
    """CLI consent: open a browser, wait for the redirect, cache the refresh token."""
    _relax_scope_check()
    store = store or FileCredentialStore()
    flow = InstalledAppFlow.from_client_secrets_file(str(_require_client_secrets()), SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh_token even on reconnect.
    credentials = flow.run_local_server(port=port, access_type="offline", prompt="consent")
    store.save(key, credentials)
    return credentials


def get_or_create_credentials(
    store: CredentialStore | None = None, key: str = DEFAULT_KEY
) -> Credentials:
    """Load cached credentials, falling back to an interactive consent prompt."""
    store = store or FileCredentialStore()
    try:
        return load_credentials(store, key)
    except NotAuthenticated:
        return run_installed_app_flow(store, key)


def build_web_flow(redirect_uri: str = YOUTUBE_OAUTH_REDIRECT_URI) -> Flow:
    """Flow for the redirect-based web consent used by the FastAPI routes."""
    _relax_scope_check()
    flow = Flow.from_client_secrets_file(str(_require_client_secrets()), SCOPES)
    flow.redirect_uri = redirect_uri
    return flow


def finish_web_flow(
    flow: Flow, authorization_response: str, store: CredentialStore, key: str
) -> Credentials:
    """Exchange the callback URL for tokens and store them under `key`."""
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials
    store.save(key, credentials)
    return credentials
