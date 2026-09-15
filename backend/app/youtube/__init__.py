"""YouTube integration: public Data API v3 + private Analytics API v2.

Other backend parts should import from here and nothing deeper.

    from app.youtube import YouTubeService

    yt = YouTubeService()
    if yt.is_connected():
        stats = yt.get_retention_stats("https://youtube.com/shorts/D0YwrMdU-uk")
"""

from .errors import (
    InvalidVideoReference,
    NoDataAvailable,
    NotAuthenticated,
    NotChannelOwner,
    QuotaExceeded,
    YouTubeError,
)
from .models import (
    ChannelMetadata,
    DayPoint,
    TrafficSource,
    VideoMetadata,
    VideoPerformance,
)
from .parsing import parse_iso8601_duration, resolve_video_id
from .service import YouTubeService

__all__ = [
    "YouTubeService",
    "ChannelMetadata",
    "VideoMetadata",
    "VideoPerformance",
    "DayPoint",
    "TrafficSource",
    "resolve_video_id",
    "parse_iso8601_duration",
    "YouTubeError",
    "NotAuthenticated",
    "NotChannelOwner",
    "QuotaExceeded",
    "NoDataAvailable",
    "InvalidVideoReference",
]
