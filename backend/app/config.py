import os
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env regardless of the current working directory.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


def require_gemini_key() -> str:
    """Fail when Gemini is actually used, not at import.

    The YouTube routes work without a Gemini key, so a missing one must not stop
    the whole app from booting.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is missing. Put it in backend/.env")
    return GEMINI_API_KEY
