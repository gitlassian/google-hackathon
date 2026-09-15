import pytest

from app.youtube.mapping import (
    curve_from_retention_rows,
    derive_stayed_to_watch_pct,
    group_by_content_type,
    rows_as_dicts,
)


def test_zips_a_reports_query_response_into_dicts():
    response = {
        "columnHeaders": [{"name": "video"}, {"name": "views"}],
        "rows": [["abc12345678", 1000], ["def12345678", 20]],
    }

    assert rows_as_dicts(response) == [
        {"video": "abc12345678", "views": 1000},
        {"video": "def12345678", "views": 20},
    ]


def test_returns_no_dicts_when_youtube_suppressed_the_rows():
    assert rows_as_dicts({"columnHeaders": [{"name": "video"}]}) == []


def test_maps_elapsed_ratio_to_seconds_and_watch_ratio_to_percent():
    rows = [
        {"elapsedVideoTimeRatio": 0.01, "audienceWatchRatio": 1.2},
        {"elapsedVideoTimeRatio": 0.5, "audienceWatchRatio": 0.6},
        {"elapsedVideoTimeRatio": 1.0, "audienceWatchRatio": 0.45},
    ]

    points = curve_from_retention_rows(rows, duration_sec=30)

    assert [(p.t, p.pct) for p in points] == [(0.3, 120.0), (15.0, 60.0), (30.0, 45.0)]


def test_keeps_the_curve_starting_where_youtube_starts_it_rather_than_at_zero():
    # elapsedVideoTimeRatio runs 0.01..1.00 — there is no t=0 row, and inventing
    # one would fabricate the single most important number in the report.
    rows = [{"elapsedVideoTimeRatio": 0.01, "audienceWatchRatio": 1.0}]

    points = curve_from_retention_rows(rows, duration_sec=60)

    assert len(points) == 1
    assert points[0].t == pytest.approx(0.6)


def test_sorts_rows_that_arrive_out_of_order():
    rows = [
        {"elapsedVideoTimeRatio": 1.0, "audienceWatchRatio": 0.4},
        {"elapsedVideoTimeRatio": 0.01, "audienceWatchRatio": 1.0},
    ]

    points = curve_from_retention_rows(rows, duration_sec=10)

    assert [p.t for p in points] == [0.1, 10.0]


def test_refuses_to_build_a_curve_without_a_known_duration():
    rows = [{"elapsedVideoTimeRatio": 0.5, "audienceWatchRatio": 1.0}]

    with pytest.raises(ValueError):
        curve_from_retention_rows(rows, duration_sec=0)


def test_derives_stayed_to_watch_from_engaged_views():
    assert derive_stayed_to_watch_pct(views=1000, engaged_views=165) == 16.5


def test_has_no_stayed_to_watch_without_both_numbers():
    assert derive_stayed_to_watch_pct(views=0, engaged_views=0) is None
    assert derive_stayed_to_watch_pct(views=100, engaged_views=None) is None
    assert derive_stayed_to_watch_pct(views=None, engaged_views=10) is None


def test_never_reports_more_than_a_hundred_percent_stayed():
    assert derive_stayed_to_watch_pct(views=100, engaged_views=110) == 100.0


def test_splits_videos_by_creator_content_type():
    rows = [
        {"video": "a", "creatorContentType": "SHORTS"},
        {"video": "b", "creatorContentType": "VIDEO_ON_DEMAND"},
        {"video": "c", "creatorContentType": "SHORTS"},
    ]

    grouped = group_by_content_type(rows)

    assert [r["video"] for r in grouped["SHORTS"]] == ["a", "c"]
    assert [r["video"] for r in grouped["VIDEO_ON_DEMAND"]] == ["b"]


def test_treats_a_missing_content_type_as_unspecified():
    grouped = group_by_content_type([{"video": "a"}])

    assert [r["video"] for r in grouped["UNSPECIFIED"]] == ["a"]
