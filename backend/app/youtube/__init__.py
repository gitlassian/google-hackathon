"""YouTube integration: public Data API v3 + private Analytics API v2.

Other backend parts should import from here and nothing deeper.
"""

from .errors import (
    InvalidVideoReference,
    NoDataAvailable,
    NotAuthenticated,
    NotChannelOwner,
    QuotaExceeded,
    YouTubeError,
)

__all__ = [
    "YouTubeError",
    "NotAuthenticated",
    "NotChannelOwner",
    "QuotaExceeded",
    "NoDataAvailable",
    "InvalidVideoReference",
]
