"""Exercise every facade method against the connected channel and report which
fields actually carry data.

    python youtube_check.py

Run this before a demo. It is the fastest way to see that credentials still work,
that retention comes back for every video, and that nothing is silently null.
Fields that are None, empty or zero are flagged with `!!`.
"""

from app.console import use_utf8_stdout

use_utf8_stdout()

from app.youtube import YouTubeService
from app.youtube.errors import YouTubeError

yt = YouTubeService()

print("=" * 78)
print("CHANNEL")
print("=" * 78)
ch = yt.get_my_channel()
for field, value in ch.model_dump().items():
    mark = "  " if value not in (None, "", 0) else "!!"
    print(f"{mark} {field:22} {str(value)[:70]}")

print()
print("=" * 78)
print("CHANNEL SUMMARY")
print("=" * 78)
summary = yt.get_channel_summary()
for field, value in summary.items():
    mark = "  " if value not in (None, "", 0, []) else "!!"
    print(f"{mark} {field:26} {str(value)[:70]}")

print()
print("=" * 78)
print("ALL VIDEOS — per-video analytics")
print("=" * 78)
videos = yt.list_my_videos(limit=200)
print(f"{len(videos)} videos returned\n")

header = f"{'video':13} {'views':>6} {'engd':>5} {'stay%':>6} {'avgDur':>7} {'avg%':>7} {'dur':>5} {'likes':>6} {'cmts':>5} {'shr':>4} {'subs':>5}"
print(header)
print("-" * len(header))
for v in videos:
    print(
        f"{v.video_id:13} {str(v.views):>6} {str(v.engaged_views):>5} "
        f"{str(v.stayed_to_watch_pct):>6} {str(v.average_view_duration_sec):>7} "
        f"{str(v.average_view_percentage):>7} {str(v.duration_sec):>5} "
        f"{str(v.likes):>6} {str(v.comments):>5} {str(v.shares):>4} {str(v.subscribers_gained):>5}"
    )

print()
print("=" * 78)
print("RETENTION — every video")
print("=" * 78)
ok = empty = failed = 0
for v in videos:
    try:
        stats = yt.get_retention_stats(v.video_id)
    except YouTubeError as exc:
        empty += 1
        print(f"  {v.video_id:13} views={str(v.views):>4}  NO DATA  ({type(exc).__name__})")
        continue
    except Exception as exc:
        failed += 1
        print(f"  {v.video_id:13} ERROR  {type(exc).__name__}: {exc}")
        continue
    ok += 1
    curve = stats.retention_curve
    drop = stats.biggest_drops[0] if stats.biggest_drops else None
    print(
        f"  {v.video_id:13} views={str(v.views):>4}  {len(curve):3} pts  "
        f"start={stats.curve_start_pct:>7}  end={stats.curve_end_pct:>7}  "
        f"dur={stats.video_duration_sec}  "
        f"biggestDrop={f'{drop.drop_pct_points}pp @ {drop.to_sec}s' if drop else 'none'}"
    )
print(f"\n  curve returned: {ok}   no data: {empty}   errors: {failed}")

print()
print("=" * 78)
print("TRAFFIC SOURCES + TIMESERIES — top 3")
print("=" * 78)
for v in videos[:3]:
    sources = yt.get_traffic_sources(v.video_id)
    days = yt.get_video_timeseries(v.video_id)
    active = [d for d in days if d.views]
    print(f"\n  {v.video_id}  ({v.views} views)")
    print(f"    traffic sources: {[(s.source, s.views) for s in sources]}")
    print(f"    timeseries: {len(days)} days, {len(active)} with views")
    if active:
        print(f"      busiest: {max(active, key=lambda d: d.views).model_dump()}")

print()
print("=" * 78)
print("PUBLIC METADATA (no OAuth needed for this call shape)")
print("=" * 78)
meta = yt.get_video("https://www.youtube.com/shorts/" + videos[0].video_id)
for field, value in meta.model_dump().items():
    mark = "  " if value not in (None, "", 0) else "!!"
    print(f"{mark} {field:18} {str(value)[:70]}")
