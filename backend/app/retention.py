"""Retention curve maths shared by both data sources.

The screenshot path (app/extractor.py) has Gemini *report* the drops it saw; the
YouTube Analytics path has to *derive* them from an exact curve. Both end up in the
same RetentionStats, so the tidying lives here rather than in either one.
"""

from __future__ import annotations

from .schemas import CurvePoint, Drop, RetentionStats

MAX_DROPS = 5


def compute_biggest_drops(curve: list[CurvePoint], limit: int = MAX_DROPS) -> list[Drop]:
    """The steepest falls between consecutive points, largest first.

    Rises are not drops, so they are left out entirely.
    """
    points = sorted(curve, key=lambda p: p.t)
    drops = [
        Drop(
            from_sec=a.t,
            to_sec=b.t,
            from_pct=a.pct,
            to_pct=b.pct,
            drop_pct_points=round(a.pct - b.pct, 1),
        )
        for a, b in zip(points, points[1:])
        if a.pct > b.pct
    ]
    drops.sort(key=lambda d: d.drop_pct_points, reverse=True)
    return drops[:limit]


def normalize_stats(stats: RetentionStats) -> RetentionStats:
    """Sort the curve, fill in its endpoints, and order the drops by size."""
    stats.retention_curve.sort(key=lambda pt: pt.t)
    if stats.retention_curve:
        stats.curve_start_pct = stats.retention_curve[0].pct
        stats.curve_end_pct = stats.retention_curve[-1].pct
    for drop in stats.biggest_drops:
        drop.drop_pct_points = round(drop.from_pct - drop.to_pct, 1)
    stats.biggest_drops.sort(key=lambda d: d.drop_pct_points, reverse=True)
    stats.biggest_drops = stats.biggest_drops[:MAX_DROPS]
    return stats
