"""Gemini answering questions about the creator's channel, using the YouTube tools.

The loop rides the stateful Interactions API, so the conversation — and any
video already in context — survives across tool calls and follow-up turns.

    create(input=question, tools=TOOLS)
      -> status "requires_action" with function_call steps
      -> create(input=[function_result...], previous_interaction_id=...)
      -> status "completed"
"""

from __future__ import annotations

import json
from typing import Any

from google import genai
from pydantic import BaseModel

from .config import GEMINI_MODEL, require_gemini_key
from .youtube import YouTubeService
from .youtube_tools import TOOLS, run_tool

# The model asks for tools until it has what it needs. Six rounds is far more
# than any real question takes, and stops a confused model spinning forever.
MAX_TOOL_ROUNDS = 6

REQUIRES_ACTION = "requires_action"

SYSTEM_PROMPT = """
You are a YouTube Shorts retention coach with live access to this creator's own
analytics through tools.

Always call a tool before stating a number. Never estimate, recall or invent
views, retention, percentages or timestamps — if a tool did not give it to you,
say you do not have it.

Interpreting the data:
- Retention above 100% is normal on Shorts. Viewers loop, so the curve starts
  high and average view percentage can exceed 100. Do not call this an error.
- "Stayed to watch" here is derived from engaged views divided by views, not
  YouTube Studio's own figure. Say so if the exact number matters.
- Treat 0:00-0:03 as the hook window. A drop over about 15 percentage points in
  a short interval is a cliff worth explaining.
- A video can have good retention and still get few views. That is a
  distribution problem — check traffic sources before blaming the edit.

If a tool returns an error, tell the creator plainly what is missing and what
they could do about it. Do not retry the same call repeatedly.

Answer in a few sentences. Cite timestamps as MM:SS. Prefer one concrete,
actionable point over a list of generic advice.
"""


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = {}
    is_error: bool = False


class ChannelAnswer(BaseModel):
    answer: str
    interaction_id: str
    tool_calls: list[ToolCall] = []
    stopped_early: bool = False


def _client() -> genai.Client:
    return genai.Client(api_key=require_gemini_key())


def _serialize(result: Any) -> str:
    """Tool results have to go back as a JSON string.

    A raw list handed to function_result is silently discarded by the API, and
    the model then invents plausible data rather than reporting that it received
    none. Verified live: a list produced entirely fabricated videos, the same
    payload as a JSON string produced the correct answer.
    """
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, default=str)


def _function_calls(interaction) -> list[Any]:
    return [
        step
        for step in (getattr(interaction, "steps", None) or [])
        if getattr(step, "type", None) == "function_call"
    ]


def ask_channel(
    message: str,
    *,
    interaction_id: str | None = None,
    client=None,
    service=None,
    max_rounds: int = MAX_TOOL_ROUNDS,
) -> ChannelAnswer:
    """Ask a question about the channel, letting the model fetch what it needs.

    `client` and `service` are injectable so the loop can be tested without
    touching either API.
    """
    client = client or _client()
    service = service or YouTubeService()

    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        input=message,
        tools=TOOLS,
        previous_interaction_id=interaction_id,
    )

    trace: list[ToolCall] = []
    stopped_early = False

    for _ in range(max_rounds):
        calls = _function_calls(interaction)
        if not calls:
            break

        results = []
        for call in calls:
            arguments = getattr(call, "arguments", None) or {}
            outcome = run_tool(service, call.name, arguments)
            trace.append(
                ToolCall(name=call.name, arguments=arguments, is_error=outcome.is_error)
            )
            results.append(
                {
                    "type": "function_result",
                    "call_id": call.id,
                    "name": call.name,
                    "result": _serialize(outcome.result),
                    "is_error": outcome.is_error,
                }
            )

        interaction = client.interactions.create(
            model=GEMINI_MODEL,
            input=results,
            tools=TOOLS,
            previous_interaction_id=interaction.id,
        )
    else:
        # Fell out of the loop still wanting tools.
        stopped_early = bool(_function_calls(interaction))

    return ChannelAnswer(
        answer=getattr(interaction, "output_text", "") or "",
        interaction_id=interaction.id,
        tool_calls=trace,
        stopped_early=stopped_early,
    )
