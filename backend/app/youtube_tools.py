"""The YouTube facade, described so Gemini can call it.

Six tools, deliberately. Large tool lists measurably hurt selection accuracy,
and these six cover every question the coaching product actually asks.

Nothing here knows about Gemini beyond the declaration format — the loop lives
in app/channel_agent.py.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from .retention import compute_biggest_drops
from .schemas import CurvePoint
from .youtube.errors import YouTubeError

CURVE_SAMPLE_POINTS = 12

_VIDEO_ID = {
    "video_id": {
        "type": "string",
        "description": "YouTube video ID, e.g. D0YwrMdU-uk. Call resolve_video first if you only have a URL.",
    }
}

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "list_my_shorts",
        "description": (
            "List the creator's own Shorts, best performing first, with views, "
            "stayed-to-watch percentage, average view percentage and duration. "
            "Start here when the question compares videos or asks which one is best or worst."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "How many Shorts to return. Default 20.",
                }
            },
        },
    },
    {
        "type": "function",
        "name": "get_video_stats",
        "description": (
            "Performance of one video: views, engaged views, stayed-to-watch, "
            "average view duration and percentage, likes, comments, shares, subscribers gained."
        ),
        "parameters": {"type": "object", "properties": _VIDEO_ID, "required": ["video_id"]},
    },
    {
        "type": "function",
        "name": "get_retention_curve",
        "description": (
            "The audience retention curve for one video, thinned to about a dozen "
            "points, plus the steepest drops and the video duration. Use this to "
            "explain where and why viewers leave. Values above 100% are normal on "
            "Shorts because viewers loop."
        ),
        "parameters": {"type": "object", "properties": _VIDEO_ID, "required": ["video_id"]},
    },
    {
        "type": "function",
        "name": "get_traffic_sources",
        "description": (
            "Where a video's views came from — Shorts feed, search, channel page, "
            "external. Use this for reach and distribution questions rather than editing ones."
        ),
        "parameters": {"type": "object", "properties": _VIDEO_ID, "required": ["video_id"]},
    },
    {
        "type": "function",
        "name": "get_channel_summary",
        "description": (
            "Channel-wide totals: views, engaged views, watch time, subscribers "
            "gained and lost, and a breakdown by content type."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "type": "function",
        "name": "resolve_video",
        "description": "Turn a YouTube URL into the video ID the other tools expect.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "Any YouTube video URL"}},
            "required": ["url"],
        },
    },
]


class ToolOutcome(NamedTuple):
    result: Any
    is_error: bool


def downsample_curve(
    points: list[CurvePoint], target: int = CURVE_SAMPLE_POINTS
) -> list[dict[str, float]]:
    """Thin a 100-point curve to roughly `target` evenly spaced points.

    Sent raw, a full curve costs about 2k tokens per call for a shape the model
    reads perfectly well from a dozen. The first and last points always survive.
    """
    if not points:
        return []
    if len(points) <= target:
        chosen = points
    else:
        step = (len(points) - 1) / (target - 1)
        chosen = [points[round(i * step)] for i in range(target)]
    return [{"t": point.t, "pct": point.pct} for point in chosen]


# --- handlers -------------------------------------------------------------


def _list_my_shorts(service, limit: int = 20) -> list[dict[str, Any]]:
    return [
        {
            "video_id": short.video_id,
            "title": short.title,
            "views": short.views,
            "stayed_to_watch_pct": short.stayed_to_watch_pct,
            "average_view_percentage": short.average_view_percentage,
            "duration_sec": short.duration_sec,
        }
        for short in service.list_my_shorts(limit=limit)
    ]


def _get_video_stats(service, video_id: str) -> dict[str, Any]:
    performance = service.get_video_performance(video_id)
    if performance is None:
        raise YouTubeError(f"No analytics for {video_id}; the channel may not own it.")
    return performance.model_dump()


def _get_retention_curve(service, video_id: str) -> dict[str, Any]:
    stats = service.get_retention_stats(video_id)
    return {
        "video_id": video_id,
        "duration_sec": stats.video_duration_sec,
        "stayed_to_watch_pct": stats.stayed_to_watch_pct,
        "curve_start_pct": stats.curve_start_pct,
        "curve_end_pct": stats.curve_end_pct,
        "curve": downsample_curve(stats.retention_curve),
        "biggest_drops": [
            drop.model_dump() for drop in compute_biggest_drops(stats.retention_curve)
        ],
        "notes": stats.notes,
    }


def _get_traffic_sources(service, video_id: str) -> list[dict[str, Any]]:
    return [source.model_dump() for source in service.get_traffic_sources(video_id)]


def _get_channel_summary(service) -> dict[str, Any]:
    return service.get_channel_summary()


def _resolve_video(service, url: str) -> dict[str, str]:
    return {"video_id": service.resolve_video_id(url)}


HANDLERS = {
    "list_my_shorts": _list_my_shorts,
    "get_video_stats": _get_video_stats,
    "get_retention_curve": _get_retention_curve,
    "get_traffic_sources": _get_traffic_sources,
    "get_channel_summary": _get_channel_summary,
    "resolve_video": _resolve_video,
}


def run_tool(service, name: str, arguments: dict[str, Any] | None) -> ToolOutcome:
    """Dispatch one tool call.

    Never raises. A failure the model caused — an unknown tool, a video the
    channel does not own, a disconnected account — comes back as an error
    *result* so the model can explain itself and carry on, rather than taking
    down the conversation.
    """
    handler = HANDLERS.get(name)
    if handler is None:
        return ToolOutcome({"error": f"No such tool: {name}"}, True)

    kwargs = {
        key: value
        for key, value in (arguments or {}).items()
        if key in handler.__code__.co_varnames
    }
    try:
        return ToolOutcome(handler(service, **kwargs), False)
    except YouTubeError as exc:
        return ToolOutcome({"error": str(exc)}, True)
    except Exception as exc:  # a broken tool must not break the conversation
        return ToolOutcome({"error": f"{type(exc).__name__}: {exc}"}, True)
