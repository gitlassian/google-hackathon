from app.youtube.models import DayPoint
from app.youtube.service import trim_empty_days


def days(*views: int) -> list[DayPoint]:
    return [DayPoint(day=f"2024-01-{i + 1:02d}", views=v) for i, v in enumerate(views)]


def test_drops_the_dead_days_before_a_video_existed():
    assert [d.views for d in trim_empty_days(days(0, 0, 0, 5, 3))] == [5, 3]


def test_drops_trailing_dead_days_too():
    assert [d.views for d in trim_empty_days(days(5, 3, 0, 0))] == [5, 3]


def test_keeps_quiet_days_in_the_middle():
    assert [d.views for d in trim_empty_days(days(5, 0, 0, 3))] == [5, 0, 0, 3]


def test_returns_nothing_when_a_video_never_had_a_view():
    assert trim_empty_days(days(0, 0, 0)) == []
    assert trim_empty_days([]) == []
