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

# The hook window, plus a little either side, so the model can see how fast the
# bleed slows down.
EARLY_CHECKPOINTS_SEC = (1.0, 3.0, 5.0)

SOURCE_NOTE = (
    "Exact figures from the YouTube Analytics API. No 'stayed to watch': YouTube "
    "Studio's definition is undisclosed and could not be reproduced (two different "
    "formulas each matched one video and were 3 and 46 points out on another). "
    "Judge the hook from the curve and from viewers_remaining_pct instead, or read "
    "Studio's own number off a screenshot."
)

# Two derivations of Studio's "Stayed to watch" have now been wrong:
#   engagedViews/views          33.3% vs Studio 74.4%  (i-8TOGtJxTc)
#   remaining at 1.0s           94.2% vs Studio 48.1%  (seIjJBsdCRc)
# Studio reaches its swipe figure at 1.5s on one video and 6.0s on another, so it
# is not a fixed cutoff. Do not add a third guess.
ENGAGED_VIEWS_MEANINGFUL_FROM = "2025-01-01"


def viewers_remaining_pct(
    rows: list[dict[str, Any]],
    duration_sec: float | None,
    at_seconds: float = 1.0,
) -> float | None:
    """Percentage of viewers still watching `at_seconds` into the video.

    A plain fact from the per-segment counters: everyone who started at the first
    segment, minus everyone who stopped before that point. This is NOT Studio's
    "Stayed to watch" and must never be presented as it.
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

    # Deliberately no stayed-to-watch on this path. See SOURCE_NOTE.
    stayed = None
    remaining = [
        CurvePoint(t=at, pct=pct)
        for at in EARLY_CHECKPOINTS_SEC
        if (pct := viewers_remaining_pct(rows, duration_sec, at)) is not None
    ]
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
        viewers_remaining=remaining,
        biggest_drops=compute_biggest_drops(curve),
        # Nothing was read off a chart, so there is nothing to be unsure about.
        reading_confidence=1.0,
        notes=SOURCE_NOTE,
    )
    return normalize_stats(stats)
