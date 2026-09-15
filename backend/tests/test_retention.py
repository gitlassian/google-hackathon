from app.retention import compute_biggest_drops
from app.schemas import CurvePoint


def curve(*pairs: tuple[float, float]) -> list[CurvePoint]:
    return [CurvePoint(t=t, pct=pct) for t, pct in pairs]


def test_finds_the_steepest_fall_between_consecutive_points():
    drops = compute_biggest_drops(curve((0, 100), (1, 90), (2, 88), (3, 50)))

    assert drops[0].from_sec == 2
    assert drops[0].to_sec == 3
    assert drops[0].drop_pct_points == 38


def test_orders_drops_largest_first():
    drops = compute_biggest_drops(curve((0, 100), (1, 90), (2, 88), (3, 50)))

    assert [d.drop_pct_points for d in drops] == [38, 10, 2]


def test_ignores_rises():
    drops = compute_biggest_drops(curve((0, 50), (1, 70), (2, 90)))

    assert drops == []


def test_returns_nothing_for_a_curve_too_short_to_have_a_slope():
    assert compute_biggest_drops(curve((0, 100))) == []
    assert compute_biggest_drops([]) == []


def test_caps_the_number_of_drops():
    steps = curve(*[(i, 100 - i * 10) for i in range(10)])

    assert len(compute_biggest_drops(steps)) == 5
    assert len(compute_biggest_drops(steps, limit=2)) == 2


def test_sorts_an_out_of_order_curve_before_measuring():
    drops = compute_biggest_drops(curve((3, 50), (0, 100), (2, 88), (1, 90)))

    assert drops[0].from_sec == 2
    assert drops[0].to_sec == 3
