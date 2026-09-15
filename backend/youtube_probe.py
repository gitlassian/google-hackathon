"""Probe the YouTube Analytics API for what it will actually give us.

    python youtube_probe.py
    python youtube_probe.py --start 2025-01-01 --end 2026-09-15
    python youtube_probe.py --video VIDEO_ID       # probe one specific video

Originally written to settle one question: does the audience retention report
return data for Shorts? It does — 100 rows, same as long-form. Kept around
because it also documents, against a live channel, which query shapes the API
accepts; several of them contradict the reference documentation.

Run from the backend/ directory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.console import use_utf8_stdout
from app.youtube.auth import get_or_create_credentials
from app.youtube.mapping import SHORTS, VIDEO_ON_DEMAND, rows_as_dicts

use_utf8_stdout()

# Verified to work on a live channel.
VIDEO_METRICS = "views,engagedViews,estimatedMinutesWatched,averageViewDuration,averageViewPercentage"

# Each variant adds one thing that could plausibly make the rows come back empty.
# Reading down the results shows exactly which knob matters.
RETENTION_VARIANTS = [
    ("A  minimal", "audienceWatchRatio", "video=={vid}"),
    ("B  + relativeRetentionPerformance", "audienceWatchRatio,relativeRetentionPerformance", "video=={vid}"),
    ("C  + audienceType==ORGANIC", "audienceWatchRatio,relativeRetentionPerformance", "video=={vid};audienceType==ORGANIC"),
    # Expected to come back empty: these three are not available for this report.
    ("D  segment counters", "audienceWatchRatio,startedWatching,stoppedWatching,totalSegmentImpressions", "video=={vid}"),
]


def describe_http_error(exc: HttpError) -> str:
    status = getattr(exc.resp, "status", "?")
    try:
        message = exc.error_details[0].get("message", "")
    except Exception:
        message = exc.reason or ""
    return f"HTTP {status} {message}".strip()


def query(analytics, start: str, end: str, **params) -> list[dict] | None:
    """Run one report. None means YouTube rejected the query shape."""
    try:
        response = (
            analytics.reports()
            .query(ids="channel==MINE", startDate=start, endDate=end, **params)
            .execute()
        )
    except HttpError as exc:
        print(f"    rejected: {describe_http_error(exc)}")
        return None
    return rows_as_dicts(response)


def list_videos(analytics, start: str, end: str, content_type: str) -> list[dict]:
    """Top videos of one content type, best first.

    `video` and `creatorContentType` cannot both be dimensions — YouTube rejects
    that combination — but creatorContentType *is* a valid filter, despite the
    documentation calling it dimension-only. It only accepts lowercase values.
    `sort` and `maxResults` are both mandatory on a per-video report.
    """
    return query(
        analytics,
        start,
        end,
        dimensions="video",
        metrics=VIDEO_METRICS,
        filters=f"creatorContentType=={content_type}",
        sort="-views",
        maxResults=200,
    ) or []


def fetch_metadata(youtube, video_ids: list[str]) -> dict[str, dict]:
    """Titles and ISO-8601 durations, 50 IDs per call, 1 quota unit per call."""
    out: dict[str, dict] = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        response = (
            youtube.videos()
            .list(part="snippet,contentDetails", id=",".join(chunk), maxResults=50)
            .execute()
        )
        for item in response.get("items", []):
            out[item["id"]] = {
                "title": item["snippet"]["title"],
                "duration": item["contentDetails"]["duration"],
            }
    return out


def probe_retention(analytics, video_id: str, label: str, start: str, end: str) -> None:
    print(f"\n--- audience retention: {label} ({video_id})")
    for name, metrics, filter_template in RETENTION_VARIANTS:
        try:
            response = (
                analytics.reports()
                .query(
                    ids="channel==MINE",
                    startDate=start,
                    endDate=end,
                    dimensions="elapsedVideoTimeRatio",
                    metrics=metrics,
                    filters=filter_template.format(vid=video_id),
                )
                .execute()
            )
        except HttpError as exc:
            print(f"  {name:38} ERROR  {describe_http_error(exc)}")
            continue

        rows = rows_as_dicts(response)
        print(f"  {name:38} {'OK   ' if rows else 'EMPTY'} {len(rows)} rows")
        if rows:
            print(f"      first: {rows[0]}")
            print(f"      last:  {rows[-1]}")


def main() -> int:
    today = dt.date.today()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", default=str(today - dt.timedelta(days=730)))
    parser.add_argument("--end", default=str(today))
    parser.add_argument("--video", help="probe this video ID instead of auto-picking")
    args = parser.parse_args()

    credentials = get_or_create_credentials()
    youtube = build("youtube", "v3", credentials=credentials)
    analytics = build("youtubeAnalytics", "v2", credentials=credentials)

    print(f"=== window {args.start} .. {args.end}")

    channel = youtube.channels().list(part="snippet,statistics", mine=True).execute()
    items = channel.get("items", [])
    if not items:
        print("No channel on this account. Connect an account that owns a channel.")
        return 1
    snippet, stats = items[0]["snippet"], items[0]["statistics"]
    print(f"=== channel: {snippet['title']}  ({items[0]['id']})")
    print(f"    {stats.get('videoCount', '?')} videos, {stats.get('subscriberCount', '?')} subscribers")

    if args.video:
        probe_retention(analytics, args.video, "requested video", args.start, args.end)
        return 0

    print("\n=== channel totals by content type")
    for row in query(
        analytics, args.start, args.end,
        dimensions="creatorContentType", metrics="views,engagedViews,estimatedMinutesWatched",
    ) or []:
        print(f"    {row}")

    for content_type, label in ((SHORTS, "SHORT"), (VIDEO_ON_DEMAND, "long-form control")):
        print(f"\n=== top videos: {content_type}")
        videos = list_videos(analytics, args.start, args.end, content_type)
        if not videos:
            print(f"    none in this window")
            continue
        for row in videos[:3]:
            print(f"    {row}")

        top = videos[0]
        meta = fetch_metadata(youtube, [top["video"]]).get(top["video"], {})
        print(f"\n    top {label}: {meta.get('title', '?')!r} duration={meta.get('duration', '?')}")
        probe_retention(analytics, top["video"], label, args.start, args.end)

    return 0


if __name__ == "__main__":
    sys.exit(main())
