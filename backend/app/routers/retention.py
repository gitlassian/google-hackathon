"""Retention, from whichever source can answer.

The YouTube Analytics API is exact but only works for videos on a channel the
user has connected. The Gemini screenshot reader works for anything but is a
model reading a chart. This router prefers the API and falls back.

Sync `def` routes on purpose: both Gemini and the Google client block.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..extractor import extract_retention_stats
from ..schemas import RetentionStats
from ..youtube import YouTubeService
from ..youtube.errors import YouTubeError

router = APIRouter(tags=["retention"])

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_SCREENSHOT_BYTES = 15 * 1024 * 1024


# No /extract-retention here: main.py defines it inline and that one stays.


@router.post("/retention", response_model=RetentionStats)
def retention(
    url: str | None = Form(default=None),
    screenshot: UploadFile | None = File(default=None),
) -> RetentionStats:
    """Exact numbers when we can get them, a read of the screenshot otherwise.

    Send `url` for a video on the connected channel, `screenshot` for anything
    else, or both to let the API win with the screenshot as a safety net.
    """
    if not url and not screenshot:
        raise HTTPException(400, "Send a YouTube url, a screenshot, or both")

    if url:
        youtube = YouTubeService()
        if youtube.is_connected():
            try:
                return youtube.get_retention_stats(url)
            except YouTubeError as exc:
                # Not ours, too few views, out of quota — the screenshot may still work.
                if not screenshot:
                    raise HTTPException(404, str(exc)) from exc

    if not screenshot:
        raise HTTPException(
            401,
            "No connected channel that owns this video, and no screenshot to fall back on",
        )
    return _from_screenshot(screenshot)


def _from_screenshot(screenshot: UploadFile) -> RetentionStats:
    if screenshot.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            400, f"Unsupported file type {screenshot.content_type}; use PNG, JPEG or WebP"
        )
    data = screenshot.file.read()
    if len(data) > MAX_SCREENSHOT_BYTES:
        raise HTTPException(413, "Screenshot larger than 15 MB")
    try:
        return extract_retention_stats(data, screenshot.content_type)
    except Exception as exc:  # surface Gemini errors during the hackathon
        raise HTTPException(502, f"Gemini extraction failed: {exc}") from exc
