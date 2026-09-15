"""Low-view videos still get a curve.

startedWatching/stoppedWatching are suppressed below some view threshold, and
asking for them takes the whole query down with it: a video with 57 views
returned 100 rows for audienceWatchRatio alone and 0 rows with the counters
added. The curve matters more than the hook number, so fall back.
"""

from app.youtube.analytics_api import RETENTION_METRICS, SAFE_RETENTION_METRICS, AnalyticsApiClient


def client_with(*responses):
    """An AnalyticsApiClient whose query() replays scripted responses."""
    client = object.__new__(AnalyticsApiClient)
    calls: list[dict] = []

    def query(**params):
        calls.append(params)
        return responses[len(calls) - 1] if len(calls) <= len(responses) else []

    client.query = query
    client.calls = calls
    return client


ROWS = [{"elapsedVideoTimeRatio": 0.01, "audienceWatchRatio": 1.6}]


def test_asks_for_the_dropoff_counters_first():
    client = client_with(ROWS)

    client.retention("abc")

    assert client.calls[0]["metrics"] == RETENTION_METRICS
    assert len(client.calls) == 1


def test_retries_without_the_counters_when_they_suppress_the_whole_result():
    client = client_with([], ROWS)

    rows = client.retention("abc")

    assert rows == ROWS
    assert client.calls[1]["metrics"] == SAFE_RETENTION_METRICS


def test_gives_up_when_even_the_plain_curve_is_empty():
    client = client_with([], [])

    assert client.retention("abc") == []
    assert len(client.calls) == 2


def test_the_safe_set_does_not_include_the_counters():
    assert "startedWatching" not in SAFE_RETENTION_METRICS
    assert "startedWatching" in RETENTION_METRICS
