"""Turning YouTube Analytics rows into the shapes the rest of the backend uses."""

from __future__ import annotations

from typing import Any

from ..retention import compute_biggest_drops, normalize_stats
from ..schemas import CurvePoint, RetentionStats

UNSPECIFIED = "UNSPECIFIED"

STAYED_TO_WATCH_NOTE = (
    "stayed_to_watch_pct is derived as engagedViews / views; YouTube Studio's own "
    "figure is not exposed by the Analytics API."
)


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
    """Split per-video rows by creatorContentType (SHORTS, VIDEO_ON_DEMAND, ...).

    creatorContentType is dimension-only — YouTube rejects it as a filter — so the
    split has to happen here rather than in the query.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row.get("creatorContentType") or UNSPECIFIED, []).append(row)
    return grouped


def retention_stats_from_analytics(
    rows: list[dict[str, Any]],
    duration_sec: float | None,
    performance: dict[str, Any] | None = None,
) -> RetentionStats:
    """Assemble the same RetentionStats the screenshot path returns, from exact data.

    `rows` are audience retention rows; `performance` is one row of per-video
    metrics (views, engagedViews, estimatedMinutesWatched, averageViewDuration).
    Keeping the output type identical is what lets the coaching prompt and the
    frontend stay unaware of which source was used.
    """
    metrics = performance or {}
    views = metrics.get("views")
    engaged_views = metrics.get("engagedViews")
    minutes_watched = metrics.get("estimatedMinutesWatched")

    stayed = derive_stayed_to_watch_pct(views, engaged_views)
    curve = curve_from_retention_rows(rows, duration_sec)

    stats = RetentionStats(
        source="analytics_api",
        video_duration_sec=duration_sec,
        avg_view_duration_sec=metrics.get("averageViewDuration"),
        engaged_views=engaged_views,
        watch_time_hours=round(minutes_watched / 60, 2) if minutes_watched else None,
        stayed_to_watch_pct=stayed,
        swiped_away_pct=round(100 - stayed, 1) if stayed is not None else None,
        retention_curve=curve,
        biggest_drops=compute_biggest_drops(curve),
        # Nothing was read off a chart, so there is nothing to be unsure about.
        reading_confidence=1.0,
        notes=STAYED_TO_WATCH_NOTE if stayed is not None else "",
    )
    return normalize_stats(stats)
