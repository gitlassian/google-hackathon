from typing import Literal, Optional

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class CurvePoint(BaseModel):
    t: float = Field(description="Seconds from the start of the video")
    pct: float = Field(description="Retention percentage at that second (can exceed 100 on Shorts)")


class FrontendModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

class ExtractedAnalytics(FrontendModel):
    duration_sec: float = Field(
        alias="durationSec",
        ge=0,
        description="Video duration in seconds read from the screenshot/video.",
    )
    stayed_to_watch_pct: float = Field(
        alias="stayedToWatchPct",
        ge=0,
        le=100,
        description="'Stayed to watch' percentage from YouTube Studio.",
    )
    avg_view_duration_sec: float = Field(
        alias="avgViewDurationSec",
        ge=0,
        description="Average view duration converted to seconds.",
    )
    curve: list[CurvePoint] = Field(
        description="Retention curve sampled from the screenshot."
    )


class HookAnalysis(FrontendModel):
    rating: Literal["strong", "ok", "weak"]
    first_three_seconds: str = Field(
        alias="firstThreeSeconds",
        description=(
            "Concrete description of what is visible and audible "
            "during 00:00-00:03."
        ),
    )
    why_it_works_or_fails: str = Field(
        alias="whyItWorksOrFails",
        description="Evidence-based explanation of hook performance.",
    )
    rewrite: str = Field(
        description=(
            "A concrete better opening for the creator's next Short "
            "on the same topic."
        ),
    )


class RetentionDip(FrontendModel):
    t: str = Field(
        description="Timestamp in MM:SS format."
    )
    drop_pct: float = Field(
        alias="dropPct",
        ge=0,
        description="Approximate retention drop in percentage points.",
    )
    on_screen: str = Field(
        alias="onScreen",
        description="What is actually visible/audible around the dip.",
    )
    cause: str = Field(
        description="Most likely reason this moment loses viewers.",
    )
    fix: str = Field(
        description="Actionable lesson for the creator's next video.",
    )


class StayedToWatchAnalysis(FrontendModel):
    rating: Literal["strong", "ok", "weak"]
    explanation: str


class ShortReport(FrontendModel):
    score: int = Field(
        ge=0,
        le=100,
        description="Overall Short retention/coaching score.",
    )
    verdict: str = Field(
        description="One concise sentence summarizing the main problem or strength."
    )
    extracted: ExtractedAnalytics
    hook: HookAnalysis
    dips: list[RetentionDip]
    stayed_to_watch: StayedToWatchAnalysis = Field(
        alias="stayedToWatch"
    )
    next_video_rules: list[str] = Field(
        alias="nextVideoRules",
        min_length=3,
        max_length=5,
        description="3-5 concrete rules for the creator's next Short.",
    )
    distribution_note: Optional[str] = Field(
        default=None,
        alias="distributionNote",
        description=(
            "Only use when the supplied evidence supports a distribution-related observation."
        ),
    )


# Defined after ShortReport because it references it. Same class, same fields —
# only the position in the file changed, so the name exists when it is used.
class AnalyzeShortResponse(BaseModel):
    interaction_id: str
    report: ShortReport


class YouTubeQuestionRequest(BaseModel):
    url: AnyHttpUrl
    question: str = Field(min_length=1, max_length=2000)

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, url: AnyHttpUrl):
        allowed_hosts = {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
        }

        if url.host not in allowed_hosts:
            raise ValueError("URL must point to YouTube")

        return url


class TimestampEvidence(BaseModel):
    timestamp: str
    description: str


class YouTubeAnswer(BaseModel):
    answer: str
    evidence: list[TimestampEvidence] = Field(default_factory=list)


class YouTubeQuestionResponse(BaseModel):
    interaction_id: str
    result: YouTubeAnswer


class FollowUpRequest(BaseModel):
    interaction_id: str
    question: str = Field(min_length=1, max_length=2000)


class RetentionStats(BaseModel):
    """Retention statistics for one video, from either data source.

    Produced by reading a YouTube Studio screenshot with Gemini, or by querying the
    YouTube Analytics API for a channel the user owns. Consumers check `source` to
    know whether they are looking at exact numbers or a model's reading of a chart.

    Any field the source does not provide is null.
    """

    source: Literal["analytics_api", "screenshot"] = Field(
        default="screenshot",
        description=(
            "Where these numbers came from. Set by the backend after the fact — "
            "do not infer it from the image."
        ),
    )
    screenshot_type: Optional[Literal["retention", "engagement_overview", "mixed", "other"]] = Field(
        default=None,
        description=(
            "Only meaningful for the screenshot source. "
            "'retention' = Audience retention panel with a curve; "
            "'engagement_overview' = top Engagement tab with views/watch time and the "
            "'How viewers engaged' bar; 'mixed' = both visible; 'other' = neither."
        ),
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
    viewers_remaining: list[CurvePoint] = Field(
        default_factory=list,
        description=(
            "Share of viewers still watching at a few early timestamps (t in seconds). "
            "Computed from drop-off counters on the API path; empty on the screenshot path. "
            "This is NOT YouTube Studio's 'Stayed to watch'."
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
