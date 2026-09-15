import pytest

from app.youtube.errors import InvalidVideoReference
from app.youtube.parsing import parse_iso8601_duration, resolve_video_id

VIDEO_ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "value",
    [
        VIDEO_ID,
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"http://youtube.com/watch?v={VIDEO_ID}",
        f"https://m.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/live/{VIDEO_ID}",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
    ],
)
def test_resolves_every_youtube_url_shape(value):
    assert resolve_video_id(value) == VIDEO_ID


@pytest.mark.parametrize(
    "value",
    [
        f"https://youtu.be/{VIDEO_ID}?t=10",
        f"https://www.youtube.com/shorts/{VIDEO_ID}?feature=share",
        f"https://www.youtube.com/watch?v={VIDEO_ID}&list=PL123&index=2",
        f"  https://www.youtube.com/shorts/{VIDEO_ID}  ",
    ],
)
def test_ignores_trailing_query_parameters_and_whitespace(value):
    assert resolve_video_id(value) == VIDEO_ID


@pytest.mark.parametrize(
    "value",
    [
        "",
        "not a url",
        "https://www.youtube.com/channel/UCuAXFkgsw1L7xaCfnd5JJOw",
        "https://www.youtube.com/@somehandle",
        "https://vimeo.com/123456",
        "https://www.youtube.com/watch?v=tooshort",
    ],
)
def test_rejects_anything_that_is_not_a_video(value):
    with pytest.raises(InvalidVideoReference):
        resolve_video_id(value)


@pytest.mark.parametrize(
    ("iso", "expected"),
    [
        ("PT45S", 45.0),
        ("PT1M5S", 65.0),
        ("PT1H2M3S", 3723.0),
        ("PT2M", 120.0),
        ("PT0S", 0.0),
        ("P1DT2H", 93600.0),
    ],
)
def test_parses_iso8601_durations(iso, expected):
    assert parse_iso8601_duration(iso) == expected


@pytest.mark.parametrize("iso", ["", "1M5S", "banana", "P"])
def test_rejects_malformed_durations(iso):
    with pytest.raises(ValueError):
        parse_iso8601_duration(iso)
