"""The YouTube facade. Other backend parts should call this and nothing deeper."""

from __future__ import annotations

import re
from typing import Any

from ..schemas import RetentionStats
from .analytics_api import AnalyticsApiClient
from .auth import DEFAULT_KEY, CredentialStore, FileCredentialStore, load_credentials
from .config import YOUTUBE_API_KEY
from .data_api import DataApiClient
from .errors import NoDataAvailable, NotAuthenticated
from .mapping import SHORTS, retention_stats_from_analytics
from .models import ChannelMetadata, DayPoint, TrafficSource, VideoMetadata, VideoPerformance
from .parsing import resolve_video_id

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def publish_window_start(video: VideoMetadata | None) -> str | None:
    """The day a video went up, as a startDate.

    Queries default to the whole history, which makes YouTube scan every day back
    to 2008 for a video uploaded last year. Same 100 rows either way: 27.8s from
    2008-07-01 against 6.6s from the publish date.
    """
    published = getattr(video, "published_at", None) or ""
    match = _ISO_DATE.match(published)
    return match.group(0) if match else None


def trim_empty_days(points: list[DayPoint]) -> list[DayPoint]:
    """Drop the dead days either side of a video's life.

    Queries default to the whole history, so a video published in 2023 otherwise
    comes back with 5,000 leading rows of zero views.
    """
    active = [i for i, point in enumerate(points) if point.views]
    if not active:
        return []
    return points[active[0] : active[-1] + 1]


class YouTubeService:
    """Public metadata plus, once a channel is connected, its private analytics.

    Clients are built lazily so that constructing the service never fails and
    never costs a network call — only the methods that need credentials do.
    """

    def __init__(
        self, store: CredentialStore | None = None, key: str = DEFAULT_KEY
    ) -> None:
        self._store = store or FileCredentialStore()
        self._key = key
        self._credentials = None
        self._data: DataApiClient | None = None
        self._analytics: AnalyticsApiClient | None = None
        # Metadata is needed by nearly every call (duration, publish date) and
        # never changes mid-request. One lookup per video, not four.
        self._video_cache: dict[str, VideoMetadata | None] = {}

    # --- connection ------------------------------------------------------

    def credentials(self):
        if self._credentials is None:
            self._credentials = load_credentials(self._store, self._key)
        return self._credentials

    def is_connected(self) -> bool:
        try:
            self.credentials()
            return True
        except NotAuthenticated:
            return False

    @property
    def data(self) -> DataApiClient:
        if self._data is None:
            try:
                self._data = DataApiClient(credentials=self.credentials())
            except NotAuthenticated:
                # Public metadata still works on an API key alone.
                self._data = DataApiClient(api_key=YOUTUBE_API_KEY)
        return self._data

    @property
    def analytics(self) -> AnalyticsApiClient:
        if self._analytics is None:
            self._analytics = AnalyticsApiClient(self.credentials())
        return self._analytics

    # --- public data -----------------------------------------------------

    def resolve_video_id(self, url_or_id: str) -> str:
        return resolve_video_id(url_or_id)

    def get_video(self, url_or_id: str) -> VideoMetadata | None:
        video_id = self.resolve_video_id(url_or_id)
        if video_id not in self._video_cache:
            self._video_cache[video_id] = self.data.get_video(video_id)
        return self._video_cache[video_id]

    def _video_window(
        self, video_id: str, start: str | None, end: str | None
    ) -> tuple[str | None, str | None]:
        """Narrow an open-ended query to the video's own lifetime."""
        if start:
            return start, end
        return publish_window_start(self.get_video(video_id)), end

    def get_videos(self, video_ids: list[str]) -> list[VideoMetadata]:
        return self.data.get_videos(video_ids)

    def get_channel(self, channel_id: str) -> ChannelMetadata | None:
        return self.data.get_channel(channel_id)

    # --- private data ----------------------------------------------------

    def get_my_channel(self) -> ChannelMetadata | None:
        return self.data.get_my_channel()

    def get_channel_summary(
        self, start: str | None = None, end: str | None = None
    ) -> dict[str, Any]:
        # No channel-level stayed-to-watch: measuring it honestly needs the
        # per-segment drop-off counters, which are per video. engagedViews/views
        # looks like an answer and is not one.
        summary = dict(self.analytics.channel_summary(start, end))
        summary["byContentType"] = self.analytics.content_type_breakdown(start, end)
        return summary

    def list_my_videos(
        self,
        start: str | None = None,
        end: str | None = None,
        shorts_only: bool = False,
        limit: int = 200,
        with_titles: bool = True,
    ) -> list[VideoPerformance]:
        content_type = SHORTS if shorts_only else None
        rows = self.analytics.top_videos(start, end, content_type, limit)

        metadata: dict[str, VideoMetadata] = {}
        if with_titles and rows:
            metadata = {
                video.video_id: video
                for video in self.data.get_videos([row["video"] for row in rows])
            }

        return [_performance(row, metadata.get(row["video"])) for row in rows]

    def list_my_shorts(self, **kwargs: Any) -> list[VideoPerformance]:
        return self.list_my_videos(shorts_only=True, **kwargs)

    def get_video_performance(
        self, url_or_id: str, start: str | None = None, end: str | None = None
    ) -> VideoPerformance | None:
        video_id = self.resolve_video_id(url_or_id)
        start, end = self._video_window(video_id, start, end)
        row = self.analytics.video_performance(video_id, start, end)
        if not row:
            return None
        performance = _performance(row, self.get_video(video_id))
        performance.content_type = self.analytics.content_type_of(video_id, start, end)
        return performance

    def get_video_timeseries(
        self, url_or_id: str, start: str | None = None, end: str | None = None
    ) -> list[DayPoint]:
        video_id = self.resolve_video_id(url_or_id)
        start, end = self._video_window(video_id, start, end)
        rows = self.analytics.timeseries(video_id, start, end)
        return trim_empty_days(
            [
                DayPoint(
                    day=row["day"],
                    views=row.get("views"),
                    estimated_minutes_watched=row.get("estimatedMinutesWatched"),
                    average_view_duration_sec=row.get("averageViewDuration"),
                )
                for row in rows
            ]
        )

    def get_traffic_sources(
        self, url_or_id: str, start: str | None = None, end: str | None = None
    ) -> list[TrafficSource]:
        video_id = self.resolve_video_id(url_or_id)
        start, end = self._video_window(video_id, start, end)
        rows = self.analytics.traffic_sources(video_id, start, end)
        return [
            TrafficSource(
                source=row["insightTrafficSourceType"],
                views=row.get("views"),
                estimated_minutes_watched=row.get("estimatedMinutesWatched"),
            )
            for row in rows
        ]

    # --- the bridge into the coaching pipeline ---------------------------

    def get_retention_stats(
        self, url_or_id: str, start: str | None = None, end: str | None = None
    ) -> RetentionStats:
        """Exact retention for an owned video, shaped exactly like the screenshot path.

        Raises NoDataAvailable when YouTube returns no curve — usually too few
        views, since low-volume retention is suppressed.
        """
        video_id = self.resolve_video_id(url_or_id)
        video = self.get_video(video_id)
        start, end = self._video_window(video_id, start, end)

        rows = self.analytics.retention(video_id, start, end)
        if not rows:
            raise NoDataAvailable(
                f"No retention data for {video_id}. The channel may not own it, or the "
                "video may have too few views for YouTube to report a curve."
            )
        return retention_stats_from_analytics(
            rows=rows,
            duration_sec=video.duration_sec if video else None,
            performance=self.analytics.video_performance(video_id, start, end),
        )


def _performance(row: dict[str, Any], video: VideoMetadata | None) -> VideoPerformance:
    """Per-video metrics, without a stayed-to-watch figure.

    Measuring stayed-to-watch honestly needs the per-segment drop-off counters,
    which cost one retention call per video — too much for a list. Rank by
    average_view_percentage here, and call get_retention_stats for a real hook
    number on a specific video.
    """
    return VideoPerformance(
        video_id=row["video"],
        title=video.title if video else None,
        duration_sec=video.duration_sec if video else None,
        views=row.get("views"),
        engaged_views=row.get("engagedViews"),
        estimated_minutes_watched=row.get("estimatedMinutesWatched"),
        average_view_duration_sec=row.get("averageViewDuration"),
        average_view_percentage=row.get("averageViewPercentage"),
        stayed_to_watch_pct=None,
        likes=row.get("likes"),
        comments=row.get("comments"),
        shares=row.get("shares"),
        subscribers_gained=row.get("subscribersGained"),
    )
