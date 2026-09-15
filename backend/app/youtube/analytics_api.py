"""YouTube Analytics API v2 — the authenticated channel's own numbers.

Every query shape below was verified against a live channel. The API rejects
combinations the reference docs imply are fine, always with the same opaque
"The query is not supported", so prefer changing these carefully.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .errors import translate_http_error
from .mapping import SHORTS, rows_as_dicts

# Confirmed to work together on a dimensions=video report.
VIDEO_METRICS = (
    "views,engagedViews,estimatedMinutesWatched,averageViewDuration,"
    "averageViewPercentage,likes,comments,shares,subscribersGained"
)

# startedWatching / stoppedWatching / totalSegmentImpressions return no rows, so
# they are left out entirely.
RETENTION_METRICS = "audienceWatchRatio,relativeRetentionPerformance"

DEFAULT_LOOKBACK_DAYS = 730


def default_window() -> tuple[str, str]:
    today = dt.date.today()
    return str(today - dt.timedelta(days=DEFAULT_LOOKBACK_DAYS)), str(today)


class AnalyticsApiClient:
    def __init__(self, credentials) -> None:
        self._api = build(
            "youtubeAnalytics", "v2", credentials=credentials, cache_discovery=False
        )

    def query(self, **params: Any) -> list[dict[str, Any]]:
        """Generic reports.query passthrough, already zipped into dicts.

        New report types cost one wrapper method, not new plumbing.
        """
        params.setdefault("ids", "channel==MINE")
        start, end = default_window()
        params.setdefault("startDate", start)
        params.setdefault("endDate", end)
        try:
            response = self._api.reports().query(**params).execute()
        except HttpError as exc:
            raise translate_http_error(exc) from exc
        return rows_as_dicts(response)

    # --- video level -----------------------------------------------------

    def top_videos(
        self,
        start: str | None = None,
        end: str | None = None,
        content_type: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Best-performing videos, optionally only Shorts.

        `video` and `creatorContentType` cannot both be dimensions, but
        creatorContentType *is* a valid filter (lowercase only) despite the docs
        calling it dimension-only. `sort` and `maxResults` are both mandatory.
        """
        params: dict[str, Any] = dict(
            dimensions="video",
            metrics=VIDEO_METRICS,
            sort="-views",
            maxResults=limit,
        )
        if content_type:
            params["filters"] = f"creatorContentType=={content_type.lower()}"
        return self._with_dates(params, start, end)

    def video_performance(
        self, video_id: str, start: str | None = None, end: str | None = None
    ) -> dict[str, Any] | None:
        rows = self._with_dates(
            dict(dimensions="video", metrics=VIDEO_METRICS, filters=f"video=={video_id}",
                 sort="-views", maxResults=1),
            start,
            end,
        )
        return rows[0] if rows else None

    def content_type_of(
        self, video_id: str, start: str | None = None, end: str | None = None
    ) -> str | None:
        """Whether one video is a Short, via the only shape that allows it."""
        rows = self._with_dates(
            dict(dimensions="creatorContentType", metrics="views", filters=f"video=={video_id}"),
            start,
            end,
        )
        return rows[0]["creatorContentType"].lower() if rows else None

    def retention(
        self, video_id: str, start: str | None = None, end: str | None = None
    ) -> list[dict[str, Any]]:
        """100 points, elapsedVideoTimeRatio 0.01..1.00. Works for Shorts."""
        return self._with_dates(
            dict(
                dimensions="elapsedVideoTimeRatio",
                metrics=RETENTION_METRICS,
                filters=f"video=={video_id}",
            ),
            start,
            end,
        )

    def timeseries(
        self, video_id: str, start: str | None = None, end: str | None = None
    ) -> list[dict[str, Any]]:
        return self._with_dates(
            dict(
                dimensions="day",
                metrics="views,estimatedMinutesWatched,averageViewDuration",
                filters=f"video=={video_id}",
                sort="day",
            ),
            start,
            end,
        )

    def traffic_sources(
        self, video_id: str, start: str | None = None, end: str | None = None
    ) -> list[dict[str, Any]]:
        return self._with_dates(
            dict(
                dimensions="insightTrafficSourceType",
                metrics="views,estimatedMinutesWatched",
                filters=f"video=={video_id}",
                sort="-views",
            ),
            start,
            end,
        )

    # --- channel level ---------------------------------------------------

    def channel_summary(
        self, start: str | None = None, end: str | None = None
    ) -> dict[str, Any]:
        rows = self._with_dates(
            dict(metrics="views,engagedViews,estimatedMinutesWatched,averageViewDuration,"
                         "subscribersGained,subscribersLost,likes,comments,shares"),
            start,
            end,
        )
        return rows[0] if rows else {}

    def content_type_breakdown(
        self, start: str | None = None, end: str | None = None
    ) -> list[dict[str, Any]]:
        return self._with_dates(
            dict(
                dimensions="creatorContentType",
                metrics="views,engagedViews,estimatedMinutesWatched",
            ),
            start,
            end,
        )

    def shorts_ids(
        self, start: str | None = None, end: str | None = None, limit: int = 200
    ) -> list[str]:
        return [row["video"] for row in self.top_videos(start, end, SHORTS, limit)]

    # --- internal --------------------------------------------------------

    def _with_dates(
        self, params: dict[str, Any], start: str | None, end: str | None
    ) -> list[dict[str, Any]]:
        if start:
            params["startDate"] = start
        if end:
            params["endDate"] = end
        return self.query(**params)
