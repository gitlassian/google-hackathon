"""The bridge: Analytics rows in, the same RetentionStats the screenshot path returns."""

import pytest

from app.schemas import RetentionStats
from app.youtube.mapping import retention_stats_from_analytics

# A 30 s Short: starts above 100% from loops, cliff at the halfway mark.
# startedWatching/stoppedWatching are the real per-segment drop-off counters.
RETENTION_ROWS = [
    {"elapsedVideoTimeRatio": 0.01, "audienceWatchRatio": 1.3, "startedWatching": 1000, "stoppedWatching": 100},
    {"elapsedVideoTimeRatio": 0.25, "audienceWatchRatio": 0.9, "startedWatching": 5, "stoppedWatching": 200},
    {"elapsedVideoTimeRatio": 0.5, "audienceWatchRatio": 0.4, "startedWatching": 2, "stoppedWatching": 150},
    {"elapsedVideoTimeRatio": 1.0, "audienceWatchRatio": 0.35, "startedWatching": 0, "stoppedWatching": 50},
]

PERFORMANCE = {
    "views": 1000,
    "engagedViews": 165,
    "estimatedMinutesWatched": 120,
    "averageViewDuration": 16,
}


def build(**overrides) -> RetentionStats:
    kwargs = dict(rows=RETENTION_ROWS, duration_sec=30, performance=PERFORMANCE)
    kwargs.update(overrides)
    return retention_stats_from_analytics(**kwargs)


def test_analytics_stats_need_no_screenshot_type():
    stats = RetentionStats(source="analytics_api", reading_confidence=1.0)

    assert stats.screenshot_type is None
    assert stats.source == "analytics_api"


def test_marks_the_numbers_as_coming_from_the_api():
    stats = build()

    assert stats.source == "analytics_api"
    assert stats.screenshot_type is None


def test_reads_the_curve_at_full_confidence_because_nothing_was_guessed():
    stats = build()

    assert stats.reading_confidence == 1.0


def test_carries_the_curve_across():
    stats = build()

    assert [(p.t, p.pct) for p in stats.retention_curve] == [
        (0.3, 130.0),
        (7.5, 90.0),
        (15.0, 40.0),
        (30.0, 35.0),
    ]
    assert stats.curve_start_pct == 130.0
    assert stats.curve_end_pct == 35.0


def test_derives_the_biggest_drop_instead_of_asking_a_model_for_it():
    stats = build()

    assert stats.biggest_drops[0].from_sec == 7.5
    assert stats.biggest_drops[0].to_sec == 15.0
    assert stats.biggest_drops[0].drop_pct_points == 50.0


def test_copies_the_performance_metrics_over():
    stats = build()

    assert stats.video_duration_sec == 30
    assert stats.avg_view_duration_sec == 16
    assert stats.engaged_views == 165
    assert stats.watch_time_hours == 2.0


def test_derives_stayed_and_swiped_away_from_real_dropoff():
    # 30 s video, so 1.0 s is ratio 0.033 and only the first segment counts:
    # 100 of 1000 viewers gone.
    stats = build()

    assert stats.stayed_to_watch_pct == 90.0
    assert stats.swiped_away_pct == 10.0


def test_says_in_the_notes_where_stayed_to_watch_was_measured():
    stats = build()

    assert "still watching" in stats.notes
    assert "Studio" in stats.notes


def test_ignores_engaged_views_entirely_for_stayed_to_watch():
    # engagedViews/views equals 100% on pre-2025 data and is noise on recent
    # data. On i-8TOGtJxTc it gave 33.3% where Studio shows 74.4%.
    stats = build(engagement={"views": 200, "engagedViews": 100})

    assert stats.stayed_to_watch_pct == 90.0


def test_has_no_stayed_to_watch_without_the_dropoff_counters():
    rows = [{"elapsedVideoTimeRatio": 0.01, "audienceWatchRatio": 1.3}]

    stats = build(rows=rows)

    assert stats.stayed_to_watch_pct is None
    assert stats.swiped_away_pct is None


def test_leaves_unique_viewers_null_because_v2_has_no_such_metric():
    assert build().unique_viewers is None


def test_works_without_any_performance_metrics():
    stats = build(performance=None)

    assert stats.avg_view_duration_sec is None
    assert stats.engaged_views is None
    assert len(stats.retention_curve) == 4
    # Stayed-to-watch comes from the retention rows, so it survives.
    assert stats.stayed_to_watch_pct == 90.0


def test_refuses_to_place_a_curve_without_a_duration():
    with pytest.raises(ValueError):
        build(duration_sec=None)
