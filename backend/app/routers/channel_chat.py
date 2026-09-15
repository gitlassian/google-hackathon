"""Ask Gemini about your channel; it fetches the analytics it needs itself.

Sync `def`: both the Gemini SDK and the Google API client block, so FastAPI has
to run this in a threadpool.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..channel_agent import ChannelAnswer, ask_channel

router = APIRouter(prefix="/channel", tags=["channel-chat"])


class ChannelChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    interaction_id: str | None = Field(
        default=None, description="Pass the previous answer's id to continue the conversation."
    )


@router.post("/chat", response_model=ChannelAnswer)
def channel_chat(request: ChannelChatRequest) -> ChannelAnswer:
    try:
        return ask_channel(request.message, interaction_id=request.interaction_id)
    except RuntimeError as exc:  # missing GEMINI_API_KEY
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Channel chat failed: {exc}") from exc
