"""Route wiring that must hold without credentials or network."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.routers.youtube import handled
from app.youtube.errors import NoDataAvailable, NotAuthenticated, QuotaExceeded, YouTubeError

client = TestClient(app)


def test_the_app_boots_without_a_gemini_key():
    # app/config.py used to raise at import, which stopped the YouTube routes
    # from working on a machine that only had YouTube credentials.
    assert client.get("/health").json() == {"status": "ok"}


def test_every_route_is_registered():
    paths = app.openapi()["paths"]

    assert "/retention" in paths
    assert "/extract-retention" in paths
    assert "/youtube/videos/{video_id}/retention" in paths


def test_retention_needs_something_to_work_with():
    response = client.post("/retention", data={})

    assert response.status_code == 400


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (NotAuthenticated("nope"), 401),
        (QuotaExceeded("slow down"), 429),
        (NoDataAvailable("nothing there"), 404),
        (YouTubeError("something else"), 502),
    ],
)
def test_module_errors_become_sensible_http_codes(error, expected_status):
    def raise_it():
        raise error

    with pytest.raises(HTTPException) as caught:
        handled(raise_it)

    assert caught.value.status_code == expected_status
