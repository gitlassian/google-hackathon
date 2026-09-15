"""Stayed-to-watch from real drop-off counters, not from engagedViews.

engagedViews/views was wrong twice over: identical to views before 2025 (a flat
100%), and pure noise afterwards on an older video with a handful of recent
views. On i-8TOGtJxTc it produced 33.3% where YouTube Studio shows 74.4%, which
inverted the verdict from "strong hook" to "worst hook on the channel".
"""

import pytest

from app.youtube.mapping import stayed_to_watch_from_dropoff

# Shape of a real response: 100 segments, ratio 0.01..1.00.
ROWS = [
    {"elapsedVideoTimeRatio": 0.01, "startedWatching": 11054, "stoppedWatching": 856},
    {"elapsedVideoTimeRatio": 0.02, "startedWatching": 30, "stoppedWatching": 1653},
    {"elapsedVideoTimeRatio": 0.03, "startedWatching": 5, "stoppedWatching": 996},
    {"elapsedVideoTimeRatio": 0.04, "startedWatching": 2, "stoppedWatching": 676},
]


def test_measures_who_is_left_after_the_swipe_decision():
    # 49s video: 1.0s is ratio 0.0204, so segments 0.01 and 0.02 count.
    # (856 + 1653) / 11054 = 22.7% gone, 77.3% still there.
    assert stayed_to_watch_from_dropoff(ROWS, duration_sec=49) == pytest.approx(77.3, abs=0.1)


def test_a_longer_window_leaves_fewer_viewers():
    early = stayed_to_watch_from_dropoff(ROWS, duration_sec=49, at_seconds=1.0)
    later = stayed_to_watch_from_dropoff(ROWS, duration_sec=49, at_seconds=2.0)

    assert later < early


def test_needs_a_duration_to_know_where_one_second_falls():
    assert stayed_to_watch_from_dropoff(ROWS, duration_sec=None) is None
    assert stayed_to_watch_from_dropoff(ROWS, duration_sec=0) is None


def test_has_no_answer_without_the_counters():
    rows = [{"elapsedVideoTimeRatio": 0.01, "audienceWatchRatio": 1.6}]

    assert stayed_to_watch_from_dropoff(rows, duration_sec=49) is None


def test_has_no_answer_without_rows():
    assert stayed_to_watch_from_dropoff([], duration_sec=49) is None


def test_never_goes_negative_if_more_stopped_than_started():
    rows = [{"elapsedVideoTimeRatio": 0.01, "startedWatching": 100, "stoppedWatching": 500}]

    assert stayed_to_watch_from_dropoff(rows, duration_sec=49) == 0.0
