"""Turning YouTube Analytics rows into the shapes the rest of the backend uses."""

from __future__ import annotations

from typing import Any

from ..retention import compute_biggest_drops, normalize_stats
from ..schemas import CurvePoint, RetentionStats

# creatorContentType values. The reference docs spell these SHORTS /
# VIDEO_ON_DEMAND, but the live API returns lowercase and rejects the uppercase
# spelling in a filter with "Invalid value (SHORTS)". Lowercase is authoritative.
SHORTS = "shorts"
VIDEO_ON_DEMAND = "video_on_demand"
UNSPECIFIED = "unspecified"

# How long a Shorts viewer takes to decide to swipe. Studio's "Stayed to watch"
# measures roughly this window, though it does not say exactly where it cuts.
HOOK_DECISION_SEC = 1.0

STAYED_TO_WATCH_NOTE = (
    "stayed_to_watch_pct is the share of viewers still watching at {at}s, computed "
    "from startedWatching/stoppedWatching. YouTube Studio's own 'Stayed to watch' "
    "uses an undisclosed cutoff and will differ by a few points."
)

# Do NOT use engagedViews/views for this. It is identical to views before 2025
# (a flat 100%), and on an older video the recent window is a handful of views,
# so the ratio is noise. On i-8TOGtJxTc it gave 33.3% against Studio's 74.4%.
ENGAGED_VIEWS_MEANINGFUL_FROM = "2025-01-01"


def stayed_to_watch_from_dropoff(
    rows: list[dict[str, Any]],
    duration_sec: float | None,
    at_seconds: float = HOOK_DECISION_SEC,
) -> float | None:
    """Percentage of viewers still watching `at_seconds` into the video.

    Uses the real per-segment counters: everyone who started at the first
    segment, minus everyone who stopped in the segments up to that point.
    """
    if not rows or not duration_sec or duration_sec <= 0:
        return None
    started = rows[0].get("startedWatching")
    if not started:
        return None

    cutoff = at_seconds / duration_sec
    stopped = sum(
        row.get("stoppedWatching") or 0
        for row in rows
        if row.get("elapsedVideoTimeRatio") is not None
        and row["elapsedVideoTimeRatio"] <= cutoff
    )
    return round(max(0.0, (1 - stopped / started) * 100), 1)


def rows_as_dicts(response: dict[str, Any]) -> list[dict[str, Any]]:
    """reports.query returns parallel columnHeaders and rows; zip them back together."""
    headers = [header["name"] for header in response.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in response.get("rows", [])]


def curve_from_retention_rows(
    rows: list[dict[str, Any]], duration_sec: float
) -> list[CurvePoint]:
    """Map audience retention rows onto a seconds/percent curve.

    elapsedVideoTimeRatio runs 0.01..1.00, so the first point sits at 1% of the
    video, not at 0. We keep it there: extrapolating back to t=0 would invent the
    single number the whole hook analysis turns on.
    """
    if not duration_sec or duration_sec <= 0:
        raise ValueError("A positive video duration is required to place the curve in time")
    points = [
        CurvePoint(
            t=round(float(row["elapsedVideoTimeRatio"]) * duration_sec, 2),
            pct=round(float(row["audienceWatchRatio"]) * 100, 2),
        )
        for row in rows
        if row.get("elapsedVideoTimeRatio") is not None
        and row.get("audienceWatchRatio") is not None
    ]
    points.sort(key=lambda point: point.t)
    return points


def derive_stayed_to_watch_pct(
    views: int | None, engaged_views: int | None
) -> float | None:
    """Approximate YouTube Studio's "Stayed to watch" from engagedViews / views.

    Studio does not expose its own figure through the API. engagedViews counts
    views past the first frame, which is the closest published equivalent — but it
    is our arithmetic, not YouTube's number, so callers must label it as derived.
    """
    if not views or engaged_views is None:
        return None
    return round(min(100.0, engaged_views / views * 100), 1)


def group_by_content_type(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Split rows of a `dimensions=creatorContentType` report by content type.

    For *listing* a channel's Shorts, prefer `filters=creatorContentType==shorts`
    on a `dimensions=video` report — YouTube rejects `video` and
    `creatorContentType` as dimensions in the same query, so they cannot be
    labelled row by row.

    Keys come back lowercase, whatever case the caller's data used.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        content_type = (row.get("creatorContentType") or UNSPECIFIED).lower()
        grouped.setdefault(content_type, []).append(row)
    return grouped


def retention_stats_from_analytics(
    rows: list[dict[str, Any]],
    duration_sec: float | None,
    performance: dict[str, Any] | None = None,
    engagement: dict[str, Any] | None = None,
) -> RetentionStats:
    """Assemble the same RetentionStats the screenshot path returns, from exact data.

    `rows` are audience retention rows; `performance` is one row of per-video
    metrics (views, engagedViews, estimatedMinutesWatched, averageViewDuration).
    Keeping the output type identical is what lets the coaching prompt and the
    frontend stay unaware of which source was used.

    `engagement` optionally supplies views/engagedViews from a narrower window
    just for the stayed-to-watch ratio. See ENGAGED_VIEWS_MEANINGFUL_FROM.
    """
    metrics = performance or {}
    minutes_watched = metrics.get("estimatedMinutesWatched")

    # From the real drop-off counters. engagement is accepted for compatibility
    # but deliberately unused: engagedViews/views does not measure this.
    stayed = stayed_to_watch_from_dropoff(rows, duration_sec)
    curve = curve_from_retention_rows(rows, duration_sec)

    stats = RetentionStats(
        source="analytics_api",
        video_duration_sec=duration_sec,
        avg_view_duration_sec=metrics.get("averageViewDuration"),
        engaged_views=metrics.get("engagedViews"),
        watch_time_hours=round(minutes_watched / 60, 2) if minutes_watched else None,
        stayed_to_watch_pct=stayed,
        swiped_away_pct=round(100 - stayed, 1) if stayed is not None else None,
        retention_curve=curve,
        biggest_drops=compute_biggest_drops(curve),
        # Nothing was read off a chart, so there is nothing to be unsure about.
        reading_confidence=1.0,
        notes=(
            STAYED_TO_WATCH_NOTE.format(at=HOOK_DECISION_SEC) if stayed is not None else ""
        ),
    )
    return normalize_stats(stats)
