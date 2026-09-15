import os
import shutil
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .extractor import extract_retention_stats
from .schemas import (
    AnalyzeShortResponse,
    FollowUpRequest,
    YouTubeQuestionRequest,
    YouTubeQuestionResponse,
    RetentionStats,
)
from .gemini_video import (
    analyze_short_file,
    ask_follow_up,
    ask_youtube_video,
)
from .routers import channel_chat, retention, youtube

app = FastAPI(title="Shorts Retention Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The endpoints below stay inline. These routers only add what is not already
# here: /channel/chat, the /youtube/* analytics reads, and POST /retention.
app.include_router(channel_chat.router)
app.include_router(retention.router)
app.include_router(youtube.router)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
}


@app.post(
    "/analyze/file",
    response_model=AnalyzeShortResponse,
)
async def analyze_file(
    video: UploadFile = File(...),
    screenshot: UploadFile = File(...),
) -> AnalyzeShortResponse:

    if video.content_type not in VIDEO_TYPES:
        raise HTTPException(
            400,
            f"Unsupported video type {video.content_type}",
        )

    if screenshot.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            400,
            f"Unsupported screenshot type {screenshot.content_type}",
        )

    screenshot_data = await screenshot.read()

    suffix = os.path.splitext(
        video.filename or "video.mp4"
    )[1] or ".mp4"

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_video:
            temp_path = temp_video.name

            await video.seek(0)

            shutil.copyfileobj(
                video.file,
                temp_video,
            )

        report, interaction_id = analyze_short_file(
            video_path=temp_path,
            screenshot_bytes=screenshot_data,
            screenshot_mime_type=screenshot.content_type,
        )

        return AnalyzeShortResponse(
            interaction_id=interaction_id,
            report=report,
        )

    except Exception as exc:
        raise HTTPException(
            502,
            f"Gemini video analysis failed: {exc}",
        ) from exc

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract-retention", response_model=RetentionStats)
async def extract_retention(screenshot: UploadFile = File(...)) -> RetentionStats:
    """Upload a YouTube Studio screenshot; get stayed-to-watch and retention curve data."""
    if screenshot.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type {screenshot.content_type}; use PNG, JPEG or WebP")
    data = await screenshot.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Screenshot larger than 15 MB")
    try:
        return extract_retention_stats(data, screenshot.content_type)
    except Exception as exc:  # surface Gemini errors to the client during the hackathon
        raise HTTPException(502, f"Gemini extraction failed: {exc}") from exc


@app.post(
    "/youtube/ask",
    response_model=YouTubeQuestionResponse,
)
async def ask_youtube(
    request: YouTubeQuestionRequest,
) -> YouTubeQuestionResponse:
    try:
        result, interaction_id = ask_youtube_video(
            str(request.url),
            request.question,
        )

        return YouTubeQuestionResponse(
            interaction_id=interaction_id,
            result=result,
        )

    except Exception as exc:
        raise HTTPException(
            502,
            f"Gemini video analysis failed: {exc}",
        ) from exc


@app.post("/youtube/follow-up")
async def youtube_follow_up(
    request: FollowUpRequest,
):
    try:
        answer, interaction_id = ask_follow_up(
            request.interaction_id,
            request.question,
        )

        return {
            "interaction_id": interaction_id,
            "answer": answer,
        }

    except Exception as exc:
        raise HTTPException(
            502,
            f"Gemini follow-up failed: {exc}",
        ) from exc
