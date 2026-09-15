"""Go/no-go probe: does the YouTube Analytics API return audience retention for Shorts?

    python youtube_probe.py
    python youtube_probe.py --start 2025-01-01 --end 2026-09-15
    python youtube_probe.py --video VIDEO_ID       # force one specific video

Google's documentation never states whether the audience retention report covers
Shorts. YouTube Studio clearly shows the curve, but that is not evidence about the
API. Everything in app/youtube/ depends on the answer, so settle it before building.

Run from the backend/ directory. Prints, for a Short and for a long-form control,
how many rows each of four escalating query variants returns.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.youtube.auth import get_or_create_credentials

# Each variant adds one thing that is a plausible cause of empty rows on a Short.
# Reading down the results tells us exactly which knob breaks it.
RETENTION_VARIANTS = [
    (
        "A  minimal",
        "audienceWatchRatio",
        "video=={vid}",
    ),
    (
        "B  + relativeRetentionPerformance",
        "audienceWatchRatio,relativeRetentionPerformance",
        "video=={vid}",
    ),
    (
        "C  + audienceType==ORGANIC",
        "audienceWatchRatio,relativeRetentionPerformance",
        "video=={vid};audienceType==ORGANIC",
    ),
    (
        "D  segment counters",
        "audienceWatchRatio,startedWatching,stoppedWatching,totalSegmentImpressions",
        "video=={vid}",
    ),
]


def rows_as_dicts(response: dict) -> list[dict]:
    """Zip a reports.query response back into dicts keyed by column name."""
    headers = [h["name"] for h in response.get("columnHeaders", [])]
    return [dict(zip(headers, row)) for row in response.get("rows", [])]


def describe_http_error(exc: HttpError) -> str:
    status = getattr(exc.resp, "status", "?")
    try:
        detail = exc.error_details
    except Exception:
        detail = None
    return f"HTTP {status} {detail or exc.reason or ''}".strip()


def list_videos_by_content_type(analytics, start: str, end: str) -> list[dict]:
    """Per-video metrics labelled with creatorContentType.

    creatorContentType is a dimension, never a filter, so SHORTS has to be split
    out on our side.
    """
    base = dict(
        ids="channel==MINE",
        startDate=start,
        endDate=end,
        dimensions="video,creatorContentType",
        sort="-views",
        maxResults=200,
    )
    # engagedViews is comparatively new; fall back if it is rejected here.
    for metrics in (
        "views,engagedViews,estimatedMinutesWatched,averageViewDuration",
        "views,estimatedMinutesWatched,averageViewDuration",
    ):
        try:
            response = analytics.reports().query(metrics=metrics, **base).execute()
            print(f"  video list metrics accepted: {metrics}")
            return rows_as_dicts(response)
        except HttpError as exc:
            print(f"  video list rejected [{metrics}]: {describe_http_error(exc)}")
    return []


def fetch_titles(youtube, video_ids: list[str]) -> dict[str, dict]:
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
        verdict = "OK  " if rows else "EMPTY"
        print(f"  {name:38} {verdict} {len(rows)} rows")
        if rows:
            print(f"      first: {rows[0]}")
            if len(rows) > 1:
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

    print("\n=== videos by creatorContentType")
    videos = list_videos_by_content_type(analytics, args.start, args.end)
    if not videos:
        print("No per-video rows returned. Widen the date range, or the channel has no views yet.")
        return 1

    by_type: dict[str, list[dict]] = {}
    for row in videos:
        by_type.setdefault(row.get("creatorContentType", "UNSPECIFIED"), []).append(row)
    for content_type, rows in sorted(by_type.items()):
        total = sum(int(r.get("views", 0)) for r in rows)
        print(f"    {content_type:18} {len(rows):4} videos, {total:>9} views")

    shorts = by_type.get("SHORTS", [])
    longform = by_type.get("VIDEO_ON_DEMAND", [])
    if not shorts:
        print("\nNo SHORTS rows in this window — the retention question stays unanswered.")

    titles = fetch_titles(youtube, [r["video"] for r in (shorts[:1] + longform[:1])])

    for rows, label in ((shorts, "SHORT"), (longform, "long-form control")):
        if not rows:
            continue
        top = rows[0]
        meta = titles.get(top["video"], {})
        print(
            f"\n=== top {label}: {meta.get('title', '?')!r} "
            f"duration={meta.get('duration', '?')} views={top.get('views')} "
            f"engagedViews={top.get('engagedViews', 'n/a')} "
            f"avgViewDuration={top.get('averageViewDuration')}s"
        )
        probe_retention(analytics, top["video"], label, args.start, args.end)

    print(
        "\n=== verdict: if variant A returned ~100 rows for the SHORT, the plan holds "
        "and the screenshot path becomes a fallback. If every variant is EMPTY for the "
        "SHORT but OK for the control, Shorts retention is not exposed and the "
        "screenshot stays primary."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
