"""Gemini video analysis and follow-up Q&A.

Moved out of main.py during the merge with the YouTube module so every endpoint
lives in a router. Sync `def` rather than `async def`: the Gemini SDK blocks, so
FastAPI has to run these in a threadpool.
"""

from fastapi import APIRouter, HTTPException

from ..gemini_video import ask_follow_up, ask_youtube_video
from ..schemas import FollowUpRequest, YouTubeQuestionRequest, YouTubeQuestionResponse

router = APIRouter(tags=["video-qa"])


@router.post("/youtube/ask", response_model=YouTubeQuestionResponse)
def ask_youtube(request: YouTubeQuestionRequest) -> YouTubeQuestionResponse:
    try:
        result, interaction_id = ask_youtube_video(str(request.url), request.question)
    except Exception as exc:
        raise HTTPException(502, f"Gemini video analysis failed: {exc}") from exc
    return YouTubeQuestionResponse(interaction_id=interaction_id, result=result)


@router.post("/youtube/follow-up")
def youtube_follow_up(request: FollowUpRequest) -> dict[str, str]:
    try:
        answer, interaction_id = ask_follow_up(request.interaction_id, request.question)
    except Exception as exc:
        raise HTTPException(502, f"Gemini follow-up failed: {exc}") from exc
    return {"interaction_id": interaction_id, "answer": answer}
