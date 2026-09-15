"""The tool loop, driven by a scripted client so it needs no network."""

from types import SimpleNamespace

from app.channel_agent import MAX_TOOL_ROUNDS, ask_channel


def step(kind: str, **fields):
    return SimpleNamespace(type=kind, **fields)


def interaction(ident: str, status: str, steps=None, output_text=""):
    return SimpleNamespace(
        id=ident, status=status, steps=steps or [], output_text=output_text
    )


class FakeClient:
    """Returns scripted interactions and records what it was sent."""

    def __init__(self, *responses):
        self._responses = list(responses)
        self.requests: list[dict] = []
        self.interactions = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return self._responses.pop(0)


class FakeService:
    def get_channel_summary(self, *args, **kwargs):
        return {"views": 84762}


def test_answers_directly_when_the_model_asks_for_no_tools():
    client = FakeClient(interaction("i1", "completed", output_text="Hello"))

    result = ask_channel("hi", client=client, service=FakeService())

    assert result.answer == "Hello"
    assert result.interaction_id == "i1"
    assert result.tool_calls == []


def test_runs_a_requested_tool_and_feeds_the_result_back():
    client = FakeClient(
        interaction(
            "i1",
            "requires_action",
            steps=[step("function_call", id="c1", name="get_channel_summary", arguments={})],
        ),
        interaction("i2", "completed", output_text="You have 84,762 views."),
    )

    result = ask_channel("how many views?", client=client, service=FakeService())

    assert result.answer == "You have 84,762 views."
    assert result.interaction_id == "i2"
    assert [call.name for call in result.tool_calls] == ["get_channel_summary"]

    follow_up = client.requests[1]
    assert follow_up["previous_interaction_id"] == "i1"
    assert follow_up["input"][0]["type"] == "function_result"
    assert follow_up["input"][0]["call_id"] == "c1"


def test_sends_tool_results_as_json_strings():
    # A raw list handed to function_result is silently dropped by the API, and
    # the model then invents data rather than saying it got none. Verified
    # against the live API: list -> fabricated videos, JSON string -> correct.
    class ListService:
        def get_channel_summary(self, *args, **kwargs):
            return [{"video_id": "vwXfMBpGpQI", "views": 25307}]

    client = FakeClient(
        interaction(
            "i1",
            "requires_action",
            steps=[step("function_call", id="c1", name="get_channel_summary", arguments={})],
        ),
        interaction("i2", "completed", output_text="ok"),
    )

    ask_channel("q", client=client, service=ListService())

    sent = client.requests[1]["input"][0]["result"]
    assert isinstance(sent, str)
    assert "vwXfMBpGpQI" in sent
    assert "25307" in sent


def test_keeps_non_ascii_readable_in_tool_results():
    class CyrillicService:
        def get_channel_summary(self, *args, **kwargs):
            return {"title": "Анекдот"}

    client = FakeClient(
        interaction(
            "i1",
            "requires_action",
            steps=[step("function_call", id="c1", name="get_channel_summary", arguments={})],
        ),
        interaction("i2", "completed", output_text="ok"),
    )

    ask_channel("q", client=client, service=CyrillicService())

    assert "Анекдот" in client.requests[1]["input"][0]["result"]


def test_carries_a_conversation_forward():
    client = FakeClient(interaction("i2", "completed", output_text="Sure"))

    ask_channel("and the next one?", interaction_id="i1", client=client, service=FakeService())

    assert client.requests[0]["previous_interaction_id"] == "i1"


def test_handles_several_tool_calls_in_one_turn():
    client = FakeClient(
        interaction(
            "i1",
            "requires_action",
            steps=[
                step("function_call", id="c1", name="get_channel_summary", arguments={}),
                step("function_call", id="c2", name="get_channel_summary", arguments={}),
            ],
        ),
        interaction("i2", "completed", output_text="done"),
    )

    result = ask_channel("compare", client=client, service=FakeService())

    assert len(result.tool_calls) == 2
    assert len(client.requests[1]["input"]) == 2


def test_gives_up_rather_than_looping_forever():
    # A model that keeps asking for tools must not spin indefinitely.
    forever = [
        interaction(
            f"i{n}",
            "requires_action",
            steps=[step("function_call", id=f"c{n}", name="get_channel_summary", arguments={})],
        )
        for n in range(MAX_TOOL_ROUNDS + 5)
    ]
    client = FakeClient(*forever)

    result = ask_channel("loop please", client=client, service=FakeService())

    assert len(result.tool_calls) == MAX_TOOL_ROUNDS
    assert result.stopped_early is True


def test_passes_the_tool_declarations_on_every_round():
    client = FakeClient(
        interaction(
            "i1",
            "requires_action",
            steps=[step("function_call", id="c1", name="get_channel_summary", arguments={})],
        ),
        interaction("i2", "completed", output_text="ok"),
    )

    ask_channel("q", client=client, service=FakeService())

    assert all(request.get("tools") for request in client.requests)


def test_records_failed_tools_in_the_trace():
    client = FakeClient(
        interaction(
            "i1",
            "requires_action",
            steps=[step("function_call", id="c1", name="no_such_tool", arguments={})],
        ),
        interaction("i2", "completed", output_text="sorry"),
    )

    result = ask_channel("q", client=client, service=FakeService())

    assert result.tool_calls[0].is_error is True
    assert client.requests[1]["input"][0]["is_error"] is True
