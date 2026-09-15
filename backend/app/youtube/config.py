"""Configuration for the YouTube module.

Unlike app/config.py this must NOT raise at import time: YouTube credentials are
optional (the screenshot path still works without them), so a missing key has to
fail at call time with NotAuthenticated instead of stopping the app from booting.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BACKEND_DIR / ".env")


def _path(env_var: str, default: Path) -> Path:
    raw = os.environ.get(env_var, "")
    return Path(raw).expanduser() if raw else default


# Public Data API reads (video/channel metadata) only need an API key.
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# OAuth client downloaded from the Google Cloud console.
YOUTUBE_CLIENT_SECRETS_FILE = _path(
    "YOUTUBE_CLIENT_SECRETS_FILE", BACKEND_DIR / "client_secret.json"
)

# Where the cached refresh token lives. Gitignored via *token*.json.
YOUTUBE_TOKEN_FILE = _path("YOUTUBE_TOKEN_FILE", BACKEND_DIR / ".youtube-token.json")

# Must match a redirect URI registered on the OAuth client for the web flow.
YOUTUBE_OAUTH_REDIRECT_URI = os.environ.get(
    "YOUTUBE_OAUTH_REDIRECT_URI", "http://localhost:8000/youtube/auth/callback"
)

# Cached Analytics responses, so a repeated demo run costs no quota and still works
# if the API is unreachable on stage.
YOUTUBE_CACHE_DIR = _path("YOUTUBE_CACHE_DIR", BACKEND_DIR / ".youtube-cache")
