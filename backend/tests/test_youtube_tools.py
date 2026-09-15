import pytest

from app.schemas import CurvePoint
from app.youtube.errors import NoDataAvailable, NotAuthenticated
from app.youtube_tools import TOOLS, curve_payload, run_tool


def test_every_tool_is_declared_the_way_gemini_expects():
    for tool in TOOLS:
        assert tool["type"] == "function"
        assert tool["name"] and tool["description"]
        assert tool["parameters"]["type"] == "object"


def test_tool_names_are_unique():
    names = [tool["name"] for tool in TOOLS]

    assert len(names) == len(set(names))


def test_exposes_the_curated_set_and_nothing_else():
    assert {tool["name"] for tool in TOOLS} == {
        "list_my_shorts",
        "get_video_stats",
        "get_retention_curve",
        "get_traffic_sources",
        "get_channel_summary",
        "resolve_video",
    }


# --- curve downsampling ---------------------------------------------------


def curve(n: int) -> list[CurvePoint]:
    return [CurvePoint(t=float(i), pct=100.0 - i) for i in range(n)]


def test_sends_the_whole_curve_by_default():
    # Thinning to 12 hid the hook window entirely: a 49s Short jumped from 0.49s
    # to 4.9s, skipping all five of its steepest drops. 100 points is ~700
    # tokens, which is affordable.
    assert len(curve_payload(curve(100))) == 100


def test_can_still_thin_when_asked():
    points = curve_payload(curve(100), target=12)

    assert len(points) == 12


def test_always_keeps_the_first_and_last_point():
    points = curve_payload(curve(100), target=12)

    assert points[0]["t"] == 0.0
    assert points[-1]["t"] == 99.0


def test_leaves_a_curve_alone_when_it_is_already_short():
    points = curve_payload(curve(5), target=12)

    assert len(points) == 5


def test_handles_an_empty_curve():
    assert curve_payload([], target=12) == []


# --- dispatch -------------------------------------------------------------


class FakeService:
    def __init__(self, **behaviours):
        self._behaviours = behaviours

    def __getattr__(self, name):
        if name not in self._behaviours:
            raise AttributeError(name)
        value = self._behaviours[name]

        def call(*args, **kwargs):
            if isinstance(value, Exception):
                raise value
            return value

        return call


def test_runs_the_named_tool_and_returns_its_result():
    service = FakeService(get_channel_summary={"views": 84762})

    outcome = run_tool(service, "get_channel_summary", {})

    assert outcome.is_error is False
    assert outcome.result["views"] == 84762


def test_reports_an_unknown_tool_back_to_the_model_instead_of_raising():
    outcome = run_tool(FakeService(), "delete_everything", {})

    assert outcome.is_error is True
    assert "delete_everything" in str(outcome.result)


def test_turns_a_youtube_error_into_something_the_model_can_recover_from():
    # "You don't own that video" should let the model apologise and move on,
    # not 500 the whole conversation.
    service = FakeService(get_retention_stats=NoDataAvailable("too few views"))

    outcome = run_tool(service, "get_retention_curve", {"video_id": "abc"})

    assert outcome.is_error is True
    assert "too few views" in str(outcome.result)


def test_reports_a_disconnected_channel_as_a_tool_error():
    service = FakeService(list_my_shorts=NotAuthenticated("connect a channel first"))

    outcome = run_tool(service, "list_my_shorts", {})

    assert outcome.is_error is True
    assert "connect a channel" in str(outcome.result)


def test_an_unexpected_crash_does_not_escape_the_tool():
    service = FakeService(get_channel_summary=RuntimeError("boom"))

    outcome = run_tool(service, "get_channel_summary", {})

    assert outcome.is_error is True


def test_ignores_arguments_the_model_invented():
    service = FakeService(get_channel_summary={"views": 1})

    outcome = run_tool(service, "get_channel_summary", {"nonsense": True})

    assert outcome.is_error is False
