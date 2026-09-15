"""Turning user input into things the YouTube APIs accept."""

from __future__ import annotations

import re

from .errors import InvalidVideoReference

_VIDEO_ID = r"[A-Za-z0-9_-]{11}"

# Every URL shape that carries a video ID. Channel and handle URLs match none of
# them on purpose - they are not videos.
_URL_PATTERNS = [
    re.compile(rf"[?&]v=(?P<id>{_VIDEO_ID})(?:[&#]|$)"),
    re.compile(rf"youtu\.be/(?P<id>{_VIDEO_ID})(?:[?&/#]|$)"),
    re.compile(rf"/(?:shorts|live|embed|v)/(?P<id>{_VIDEO_ID})(?:[?&/#]|$)"),
]

_BARE_ID = re.compile(rf"^{_VIDEO_ID}$")

_DURATION = re.compile(
    r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?)?$"
)


def resolve_video_id(value: str) -> str:
    """Accept a bare ID or any YouTube video URL; return the 11-character ID.

    Raises InvalidVideoReference for channel URLs, handles and anything else that
    does not identify a single video.
    """
    candidate = (value or "").strip()
    if _BARE_ID.match(candidate):
        return candidate
    for pattern in _URL_PATTERNS:
        match = pattern.search(candidate)
        if match:
            return match.group("id")
    raise InvalidVideoReference(f"Could not find a YouTube video ID in {value!r}")


def parse_iso8601_duration(value: str) -> float:
    """Convert a Data API contentDetails.duration ("PT1M5S") to seconds."""
    match = _DURATION.match((value or "").strip())
    if not match or not any(match.groupdict().values()):
        raise ValueError(f"Not an ISO-8601 duration: {value!r}")
    parts = {k: float(v) if v else 0.0 for k, v in match.groupdict().items()}
    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )
