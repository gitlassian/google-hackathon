from typing import Literal, Optional

from pydantic import BaseModel, Field


class CurvePoint(BaseModel):
    t: float = Field(description="Seconds from the start of the video")
    pct: float = Field(description="Retention percentage at that second (can exceed 100 on Shorts)")


class RetentionStats(BaseModel):
    """Everything Gemini can read off a YouTube Studio Engagement screenshot.

    Any field that is not visible in the screenshot is null.
    """

    screenshot_type: Literal["retention", "engagement_overview", "mixed", "other"] = Field(
        description=(
            "'retention' = Audience retention panel with a curve; "
            "'engagement_overview' = top Engagement tab with views/watch time and the "
            "'How viewers engaged' bar; 'mixed' = both visible; 'other' = neither."
        )
    )
    stayed_to_watch_pct: Optional[float] = Field(
        default=None, description="'Stayed to watch' percentage, e.g. 16.5"
    )
    swiped_away_pct: Optional[float] = Field(
        default=None, description="'Swiped away' percentage if shown, e.g. 83.5"
    )
    avg_view_duration_sec: Optional[float] = Field(
        default=None, description="'Average view duration' converted to seconds (0:16 -> 16)"
    )
    video_duration_sec: Optional[float] = Field(
        default=None,
        description="Total video length in seconds, from the last x-axis label or the player (0:37 / 0:39 -> 39)",
    )
    engaged_views: Optional[int] = None
    unique_viewers: Optional[int] = None
    watch_time_hours: Optional[float] = Field(
        default=None, description="'Watch time (hours)'; note the locale may use a comma: 0,1 -> 0.1"
    )
    retention_curve: list[CurvePoint] = Field(
        default_factory=list,
        description=(
            "The pink 'This video' line sampled at roughly every 1-2 seconds from 0 to the video end. "
            "Empty if no retention chart is visible."
        ),
    )
    curve_start_pct: Optional[float] = Field(
        default=None, description="Retention value at 0:00 (often above 100 on Shorts because of rewatches)"
    )
    curve_end_pct: Optional[float] = Field(
        default=None, description="Retention value at the last second of the video"
    )
    biggest_drops: list["Drop"] = Field(
        default_factory=list,
        description="Up to 5 steepest falls in the curve, ordered by size of drop",
    )
    reading_confidence: float = Field(
        ge=0, le=1, description="How confident the extraction is, 0 to 1"
    )
    notes: str = Field(
        default="",
        description="Short remark on anything ambiguous (cropped chart, unreadable label, etc.)",
    )


class Drop(BaseModel):
    from_sec: float
    to_sec: float
    from_pct: float
    to_pct: float
    drop_pct_points: float = Field(description="from_pct - to_pct")


RetentionStats.model_rebuild()
