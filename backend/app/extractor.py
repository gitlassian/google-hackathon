"""Gemini tool: turn a YouTube Studio screenshot into retention statistics."""

import logging
import mimetypes
from pathlib import Path

from google import genai
from google.genai import types

from .config import GEMINI_MODEL, require_gemini_key
from .retention import normalize_stats
from .schemas import RetentionStats

# The SDK logs an "automatic function calling" warning on every call we make; not relevant here.
logging.getLogger("google_genai.models").setLevel(logging.ERROR)

_client_cache: genai.Client | None = None


def _client() -> genai.Client:
    """Built on first use so the app boots with only YouTube credentials."""
    global _client_cache
    if _client_cache is None:
        _client_cache = genai.Client(api_key=require_gemini_key())
    return _client_cache

EXTRACTION_PROMPT = """\
You are reading a screenshot from YouTube Studio's Analytics > Engagement tab for a YouTube Short.

Extract every statistic that is visible. Work carefully:

1. Identify what is on screen:
   - "Audience retention" panel: has "Stayed to watch", "Average view duration", a video
     preview with a player time like "0:37 / 0:39", and a pink line chart with an x-axis
     in MM:SS (0:00 ... end) and a y-axis in percent (0%, 50%, 100%, 150% or 40/80/120).
   - Engagement overview: tiles "Engaged views", "Unique viewers", "Watch time (hours)",
     "Average view duration", plus a "How viewers engaged" bar with "Stayed to watch" and
     "Swiped away" percentages.

2. Numbers:
   - Convert MM:SS to seconds. Convert "0,1" style decimals to 0.1.
   - Video duration = the last x-axis label of the retention chart, or the right side of the
     player time ("/ 0:39"), whichever is visible.
   - Any value that is not visible must be null. Never invent numbers.

3. Retention curve (only if the pink line chart is visible):
   - The x-axis runs from 0:00 on the left edge to the video duration on the right edge.
   - Read the y value of the pink line using the horizontal grid lines as reference.
     The top grid line label is the max (e.g. 150% or 120%); 0% is the bottom axis.
   - Sample the line every 1 second if the video is under 45 s, otherwise every 2 seconds,
     always including t=0 and t=duration. Percentages may exceed 100 near the start.
   - Then list the up-to-5 steepest drops (largest fall in percentage points between two
     consecutive samples or across a visible cliff).

4. Set reading_confidence lower if the chart is cropped, blurred, or a label is unreadable,
   and explain why in notes.
"""


def _load_image(path: str | Path) -> tuple[bytes, str]:
    p = Path(path)
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return p.read_bytes(), mime


def extract_retention_stats(image_bytes: bytes, mime_type: str = "image/png") -> RetentionStats:
    """Send one screenshot to Gemini and get structured retention statistics back."""
    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            EXTRACTION_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RetentionStats,
            temperature=0,
        ),
    )
    parsed = response.parsed
    if not isinstance(parsed, RetentionStats):
        # Fallback: SDK returned raw text (older SDKs) — validate it ourselves.
        parsed = RetentionStats.model_validate_json(response.text)
    # `source` is in the schema, so the model may have filled it in; it doesn't get a say.
    parsed.source = "screenshot"
    return normalize_stats(parsed)


def extract_retention_stats_from_file(path: str | Path) -> RetentionStats:
    data, mime = _load_image(path)
    return extract_retention_stats(data, mime)
