"""Error types the YouTube module raises, so callers never see googleapiclient internals."""


class YouTubeError(Exception):
    """Base class for every failure in this module."""


class NotAuthenticated(YouTubeError):
    """No usable OAuth credentials. The user has to connect their channel first."""


class NotChannelOwner(YouTubeError):
    """Analytics were requested for a video the authenticated channel does not own."""


class QuotaExceeded(YouTubeError):
    """Daily quota or rate limit hit."""


class NoDataAvailable(YouTubeError):
    """The query was valid but YouTube returned no rows.

    Normal for videos with too few views (YouTube suppresses low-volume retention data)
    or for a date range that is too recent to have been processed.
    """


class InvalidVideoReference(YouTubeError):
    """A string could not be resolved to a YouTube video ID."""


def translate_http_error(exc: Exception) -> YouTubeError:
    """Map a googleapiclient HttpError onto our own types.

    Falls back to a plain YouTubeError so callers only ever catch one hierarchy.
    """
    status = getattr(getattr(exc, "resp", None), "status", None)
    detail = str(exc)
    if status == 401:
        return NotAuthenticated(f"YouTube rejected the credentials: {detail}")
    if status == 403:
        # 403 covers both "out of quota" and "you don't own this channel"; the reason
        # string is the only way to tell them apart.
        lowered = detail.lower()
        if "quota" in lowered or "rateLimitExceeded".lower() in lowered:
            return QuotaExceeded(detail)
        return NotChannelOwner(detail)
    if status == 429:
        return QuotaExceeded(detail)
    return YouTubeError(detail)
