"""HTTP surface for the YouTube module.

Every route here is `def`, not `async def`, on purpose: the Google client is
synchronous, so FastAPI has to run these in a threadpool or they block the loop.

Path parameters are plain video IDs (a single path segment). To pass a full
YouTube URL, use the `?url=` form on /youtube/resolve or /retention.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from ..schemas import RetentionStats
from ..youtube import YouTubeService
from ..youtube.auth import DEFAULT_KEY, FileCredentialStore, build_web_flow, finish_web_flow
from ..youtube.errors import (
    InvalidVideoReference,
    NoDataAvailable,
    NotAuthenticated,
    NotChannelOwner,
    QuotaExceeded,
    YouTubeError,
)

router = APIRouter(prefix="/youtube", tags=["youtube"])

STATUS_FOR = {
    NotAuthenticated: 401,
    NotChannelOwner: 403,
    QuotaExceeded: 429,
    NoDataAvailable: 404,
    InvalidVideoReference: 400,
}


def service() -> YouTubeService:
    return YouTubeService()


def handled(call, *args: Any, **kwargs: Any):
    """Map the module's errors onto HTTP codes; anything else becomes a 502."""
    try:
        return call(*args, **kwargs)
    except YouTubeError as exc:
        raise HTTPException(STATUS_FOR.get(type(exc), 502), str(exc)) from exc


# --- connection ----------------------------------------------------------


@router.get("/status")
def status() -> dict[str, Any]:
    yt = service()
    if not yt.is_connected():
        return {"connected": False, "channel": None}
    return {"connected": True, "channel": handled(yt.get_my_channel)}


@router.get("/auth/start")
def auth_start() -> RedirectResponse:
    # oauthlib refuses a plain-http redirect URI unless told otherwise, and the
    # default callback is http://localhost:8000.
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    flow = build_web_flow()
    url, _state = flow.authorization_url(access_type="offline", prompt="consent")
    return RedirectResponse(url)


@router.get("/auth/callback")
def auth_callback(request: Request) -> dict[str, Any]:
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    flow = build_web_flow()
    finish_web_flow(flow, str(request.url), FileCredentialStore(), DEFAULT_KEY)
    return {"connected": True, "channel": handled(service().get_my_channel)}


@router.get("/resolve")
def resolve(url: str) -> dict[str, str]:
    return {"videoId": handled(service().resolve_video_id, url)}


# --- channel -------------------------------------------------------------


@router.get("/me")
def me() -> Any:
    return handled(service().get_my_channel)


@router.get("/summary")
def summary(start: str | None = None, end: str | None = None) -> dict[str, Any]:
    return handled(service().get_channel_summary, start, end)


@router.get("/shorts")
def shorts(start: str | None = None, end: str | None = None, limit: int = 50) -> list[Any]:
    return handled(service().list_my_shorts, start=start, end=end, limit=limit)


@router.get("/videos")
def videos(start: str | None = None, end: str | None = None, limit: int = 50) -> list[Any]:
    return handled(service().list_my_videos, start, end, False, limit)


# --- one video -----------------------------------------------------------


@router.get("/videos/{video_id}/stats")
def video_stats(video_id: str, start: str | None = None, end: str | None = None) -> Any:
    result = handled(service().get_video_performance, video_id, start, end)
    if result is None:
        raise HTTPException(404, f"No analytics for {video_id}")
    return result


@router.get("/videos/{video_id}/retention", response_model=RetentionStats)
def video_retention(
    video_id: str, start: str | None = None, end: str | None = None
) -> RetentionStats:
    return handled(service().get_retention_stats, video_id, start, end)


@router.get("/videos/{video_id}/timeseries")
def video_timeseries(
    video_id: str, start: str | None = None, end: str | None = None
) -> list[Any]:
    return handled(service().get_video_timeseries, video_id, start, end)


@router.get("/videos/{video_id}/traffic-sources")
def video_traffic_sources(
    video_id: str, start: str | None = None, end: str | None = None
) -> list[Any]:
    return handled(service().get_traffic_sources, video_id, start, end)


@router.get("/videos/{video_id}/metadata")
def video_metadata(video_id: str) -> Any:
    result = handled(service().get_video, video_id)
    if result is None:
        raise HTTPException(404, f"No such video: {video_id}")
    return result
