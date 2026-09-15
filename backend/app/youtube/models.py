"""Typed results returned by the YouTube facade.

Deliberately forgiving: anything YouTube omits stays None rather than failing a
request. Retention itself is returned as the shared RetentionStats from
app/schemas.py, not as a type defined here.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ChannelMetadata(BaseModel):
    channel_id: str
    title: str = ""
    description: str = ""
    thumbnail_url: Optional[str] = None
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None
    view_count: Optional[int] = None
    uploads_playlist_id: Optional[str] = None


class VideoMetadata(BaseModel):
    video_id: str
    title: str = ""
    description: str = ""
    published_at: Optional[str] = None
    duration_sec: Optional[float] = None
    thumbnail_url: Optional[str] = None
    channel_id: Optional[str] = None
    channel_title: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


class VideoPerformance(BaseModel):
    """Per-video analytics for a channel the caller owns."""

    video_id: str
    title: Optional[str] = None
    duration_sec: Optional[float] = None
    content_type: Optional[str] = None  # "shorts", "video_on_demand", ...
    views: Optional[int] = None
    engaged_views: Optional[int] = None
    estimated_minutes_watched: Optional[float] = None
    average_view_duration_sec: Optional[float] = None
    # Both of these exceed 100 on Shorts, because loops count. Not an error.
    average_view_percentage: Optional[float] = None
    stayed_to_watch_pct: Optional[float] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    subscribers_gained: Optional[int] = None


class DayPoint(BaseModel):
    day: str
    views: Optional[int] = None
    estimated_minutes_watched: Optional[float] = None
    average_view_duration_sec: Optional[float] = None


class TrafficSource(BaseModel):
    source: str
    views: Optional[int] = None
    estimated_minutes_watched: Optional[float] = None
