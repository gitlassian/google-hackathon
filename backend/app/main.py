from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .extractor import extract_retention_stats
from .schemas import (
    FollowUpRequest,
    YouTubeQuestionRequest,
    YouTubeQuestionResponse,
    RetentionStats,
)
from .youtube import ask_follow_up, ask_youtube_video

app = FastAPI(title="Shorts Retention Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


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
