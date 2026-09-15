import base64
import time
from google import genai

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .schemas import ShortReport ,YouTubeAnswer


_client = genai.Client(api_key=GEMINI_API_KEY)

SHORT_ANALYSIS_SYSTEM_PROMPT = """
You are an expert YouTube Shorts retention coach.

Your job is to analyze a YouTube Short together with a screenshot from
YouTube Studio analytics and explain WHY viewers behave the way shown
by the retention data.

Your analysis must connect analytics from the screenshot with concrete
visual and audio events in the video.

GENERAL RULES

- Base analytics claims only on values visible in the provided screenshot.
- Base video claims only on events that are actually visible or audible.
- Never invent metrics, views, percentages, demographics, or events.
- If something cannot be determined from the provided evidence, do not
  pretend that it can.
- Use timestamps in MM:SS format when referring to specific video moments.
- Distinguish observation from interpretation.
- Do not claim certainty about viewer psychology. Describe the most likely
  explanation supported by the retention curve and video evidence.
- Focus recommendations on what the creator should do in the NEXT Short,
  not on re-editing the already published video.

ANALYTICS

Read from the YouTube Studio screenshot when available:
- video duration,
- Stayed to watch percentage,
- Average view duration,
- audience retention curve.

Sample the visible retention curve sufficiently to capture its overall shape
and important drops. Do not fabricate precision that cannot be read from
the screenshot.

Remember that retention for Shorts can exceed 100% because viewers may
rewatch or loop parts of the video.

HOOK ANALYSIS

Treat 00:00-00:03 as the primary hook window.

Inspect these three seconds carefully, including:
- the first frame,
- visual motion,
- cuts,
- on-screen text,
- readability,
- spoken words,
- audio onset,
- whether the video's promise or payoff becomes clear.

Describe what actually happens before judging whether the hook works.

RETENTION DIPS

Identify the most meaningful drops in the retention curve.

For each important drop:
1. determine its approximate timestamp,
2. inspect what happens immediately before and during that moment,
3. describe the visual/audio event,
4. explain the most plausible reason it corresponds with viewer loss,
5. derive a concrete lesson for the next video.

Prioritize meaningful cliffs over tiny fluctuations caused by noisy
screenshot readings.

COACHING HEURISTICS

Use these as practical heuristics, not immutable laws:

- Stayed to watch >= 70%: generally strong.
- Stayed to watch 50-70%: generally average.
- Stayed to watch < 50%: generally weak.
- A major loss during 00:00-00:03 strongly suggests investigating the hook.
- A drop greater than roughly 15 percentage points over a short interval is
  significant and should be investigated carefully.
- Long visually static sections, delayed payoff, unclear openings, late audio,
  unreadable text and unnecessary repetition can hurt retention, but only
  mention them when they are actually present.
- Strong endings or loops may cause retention to recover near the end.

SCORING

Give an overall score from 0 to 100 based mainly on:
- strength of the first 3 seconds,
- ability to maintain attention,
- severity of retention cliffs,
- pacing,
- clarity of payoff,
- effectiveness of the ending/loop.

The score must agree with your written diagnosis.

OUTPUT QUALITY

- Be specific rather than generic.
- Prefer evidence such as:
  "At 00:07 the video switches to a static talking-head shot"
  over:
  "The middle could be more engaging."
- Keep the verdict concise.
- Return 3 to 5 concrete rules for the creator's next Short.

INPUT CONSISTENCY

Before correlating retention data with the video, verify that the screenshot
plausibly belongs to the supplied video.

Check:
- video duration,
- visible title or thumbnail,
- visible video frame,
- subject matter,
- any other identifying information.

If the screenshot clearly belongs to a different video:
- do not correlate retention drops with events in the video,
- do not infer causes for those drops,
- clearly state that the inputs are mismatched.

Never associate a retention timestamp with a video event if the timestamp
is outside the video's actual duration.

EVIDENCE SAFETY

- Do not infer when viewers swiped from "Stayed to watch" alone.
- Do not claim that viewers left within the first second unless the data
  explicitly supports that.
- Never describe content as reposted, copied, original, sponsored, viral,
  or similar unless there is direct evidence.
"""

SHORT_ANALYSIS_PROMPT = """
Analyze the supplied YouTube Studio analytics screenshot and YouTube Short.

Work through the evidence in this order:

1. Read the analytics screenshot.
2. Extract the visible duration, Stayed to watch, Average view duration,
   and retention curve.
3. Watch the entire Short with audio.
4. Inspect 00:00-00:03 especially carefully.
5. Locate the important drops visible in the retention curve.
6. Inspect what happens visually and audibly around every important drop.
7. Connect the retention behavior to specific events in the video.
8. Evaluate the hook, pacing and ending.
9. Produce practical rules for the creator's next Short.

Every specific diagnosis should be grounded in either the analytics
screenshot, the video, or both.

Return only the requested structured report.
"""

YOUTUBE_QA_SYSTEM_PROMPT = """
You are analyzing a YouTube Short.

Base your answers only on information visible or audible in the video.

When referring to a specific event:
- cite its timestamp in MM:SS format,
- distinguish visual evidence from audio evidence,
- do not invent events or statements not present in the video.

If something cannot be determined reliably from the video, say so.
"""


def ask_youtube_video(
    url: str,
    question: str,
) -> tuple[YouTubeAnswer, str]:
    interaction = _client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=YOUTUBE_QA_SYSTEM_PROMPT,
        input=[
            {
                "type": "video",
                "uri": url,
            },
            {
                "type": "text",
                "text": question,
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": YouTubeAnswer.model_json_schema(),
        },
    )

    result = YouTubeAnswer.model_validate_json(
        interaction.output_text
    )

    return result, interaction.id

def ask_follow_up(
    interaction_id: str,
    question: str,
) -> tuple[str, str]:
    interaction = _client.interactions.create(
        model=GEMINI_MODEL,
        input=question,
        previous_interaction_id=interaction_id,
        system_instruction=YOUTUBE_QA_SYSTEM_PROMPT,
    )

    return interaction.output_text, interaction.id

def analyze_short(
    youtube_url: str,
    screenshot_bytes: bytes,
    screenshot_mime_type: str = "image/png",
) -> tuple[ShortReport, str]:
    screenshot_b64 = base64.b64encode(
        screenshot_bytes
    ).decode("utf-8")

    interaction = _client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=SHORT_ANALYSIS_SYSTEM_PROMPT,
        input=[
            {
                "type": "image",
                "data": screenshot_b64,
                "mime_type": screenshot_mime_type,
            },
            {
                "type": "video",
                "uri": youtube_url,
            },
            {
                "type": "text",
                "text": SHORT_ANALYSIS_PROMPT,
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ShortReport.model_json_schema(
                by_alias=True
            ),
        },
        generation_config={
            "temperature": 0.2,
        },
    )

    report = ShortReport.model_validate_json(
        interaction.output_text
    )

    return report, interaction.id

def upload_video_file(video_path: str):
    video = _client().files.upload(file=video_path)

    while not video.state or video.state.name == "PROCESSING":
        time.sleep(2)
        video = _client().files.get(name=video.name)

    if video.state.name != "ACTIVE":
        raise RuntimeError(
            f"Video processing failed with state: {video.state.name}"
        )

    return video


def analyze_short_file(
    video_path: str,
    screenshot_bytes: bytes,
    screenshot_mime_type: str = "image/png",
) -> tuple[ShortReport, str]:
    video = upload_video_file(video_path)

    screenshot_b64 = base64.b64encode(
        screenshot_bytes
    ).decode("utf-8")

    interaction = _client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=SHORT_ANALYSIS_SYSTEM_PROMPT,
        input=[
            {
                "type": "image",
                "data": screenshot_b64,
                "mime_type": screenshot_mime_type,
            },
            {
                "type": "video",
                "uri": video.uri,
                "mime_type": video.mime_type,
            },
            {
                "type": "text",
                "text": SHORT_ANALYSIS_PROMPT,
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": ShortReport.model_json_schema(
                by_alias=True
            ),
        },
        generation_config={
            "temperature": 0.2,
        },
    )

    report = ShortReport.model_validate_json(
        interaction.output_text
    )

    return report, interaction.id
