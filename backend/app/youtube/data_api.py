"""YouTube Data API v3 — public metadata, plus the caller's own channel."""

from __future__ import annotations

from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import YOUTUBE_API_KEY
from .errors import NotAuthenticated, translate_http_error
from .models import ChannelMetadata, VideoMetadata
from .parsing import parse_iso8601_duration

BATCH = 50  # videos.list accepts 50 IDs for the same single quota unit


def _execute(request) -> dict[str, Any]:
    try:
        return request.execute()
    except HttpError as exc:
        raise translate_http_error(exc) from exc


def _int(value: Any) -> int | None:
    """Counts arrive as strings, and are absent entirely when the owner hides them."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _duration(value: Any) -> float | None:
    try:
        return parse_iso8601_duration(value)
    except (ValueError, TypeError):
        return None


def _thumbnail(thumbnails: dict[str, Any]) -> str | None:
    for size in ("maxres", "standard", "high", "medium", "default"):
        if size in thumbnails:
            return thumbnails[size].get("url")
    return None


class DataApiClient:
    """Metadata lookups. Works with OAuth credentials or a bare API key."""

    def __init__(self, credentials=None, api_key: str = YOUTUBE_API_KEY) -> None:
        if credentials is not None:
            self._api = build("youtube", "v3", credentials=credentials, cache_discovery=False)
        elif api_key:
            self._api = build("youtube", "v3", developerKey=api_key, cache_discovery=False)
        else:
            raise NotAuthenticated(
                "The Data API needs either OAuth credentials or YOUTUBE_API_KEY."
            )

    def get_videos(self, video_ids: list[str]) -> list[VideoMetadata]:
        found: list[VideoMetadata] = []
        for start in range(0, len(video_ids), BATCH):
            chunk = video_ids[start : start + BATCH]
            response = _execute(
                self._api.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=",".join(chunk),
                    maxResults=BATCH,
                )
            )
            found.extend(_video(item) for item in response.get("items", []))
        return found

    def get_video(self, video_id: str) -> VideoMetadata | None:
        videos = self.get_videos([video_id])
        return videos[0] if videos else None

    def get_my_channel(self) -> ChannelMetadata | None:
        response = _execute(
            self._api.channels().list(part="snippet,statistics,contentDetails", mine=True)
        )
        items = response.get("items", [])
        return _channel(items[0]) if items else None

    def get_channel(self, channel_id: str) -> ChannelMetadata | None:
        response = _execute(
            self._api.channels().list(
                part="snippet,statistics,contentDetails", id=channel_id
            )
        )
        items = response.get("items", [])
        return _channel(items[0]) if items else None

    def list_uploads(self, uploads_playlist_id: str, limit: int = 50) -> list[str]:
        """Video IDs from a channel's uploads playlist.

        1 quota unit per page, versus 100 for search.list — never use search.
        """
        ids: list[str] = []
        page_token = None
        while len(ids) < limit:
            response = _execute(
                self._api.playlistItems().list(
                    part="contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=min(BATCH, limit - len(ids)),
                    pageToken=page_token,
                )
            )
            ids.extend(
                item["contentDetails"]["videoId"] for item in response.get("items", [])
            )
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return ids


def _video(item: dict[str, Any]) -> VideoMetadata:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    return VideoMetadata(
        video_id=item["id"],
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
        published_at=snippet.get("publishedAt"),
        duration_sec=_duration(item.get("contentDetails", {}).get("duration")),
        thumbnail_url=_thumbnail(snippet.get("thumbnails", {})),
        channel_id=snippet.get("channelId"),
        channel_title=snippet.get("channelTitle"),
        view_count=_int(stats.get("viewCount")),
        like_count=_int(stats.get("likeCount")),
        comment_count=_int(stats.get("commentCount")),
    )


def _channel(item: dict[str, Any]) -> ChannelMetadata:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    related = item.get("contentDetails", {}).get("relatedPlaylists", {})
    return ChannelMetadata(
        channel_id=item["id"],
        title=snippet.get("title", ""),
        description=snippet.get("description", ""),
        thumbnail_url=_thumbnail(snippet.get("thumbnails", {})),
        subscriber_count=_int(stats.get("subscriberCount")),
        video_count=_int(stats.get("videoCount")),
        view_count=_int(stats.get("viewCount")),
        uploads_playlist_id=related.get("uploads"),
    )
