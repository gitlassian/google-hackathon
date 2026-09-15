"""Query from the video's publish date, not from 2008.

Full history makes YouTube scan 15 years of empty days. Identical 100-row result:
27.8s from 2008-07-01, 6.6s from the video's actual publish date.
"""

from app.youtube.models import VideoMetadata
from app.youtube.service import publish_window_start


def video(published_at):
    return VideoMetadata(video_id="abc", published_at=published_at)


def test_uses_the_day_the_video_was_published():
    assert publish_window_start(video("2023-10-24T10:28:40Z")) == "2023-10-24"


def test_has_no_start_without_a_publish_date():
    assert publish_window_start(video(None)) is None
    assert publish_window_start(None) is None


def test_ignores_a_publish_date_it_cannot_read():
    assert publish_window_start(video("last tuesday")) is None
    assert publish_window_start(video("")) is None
