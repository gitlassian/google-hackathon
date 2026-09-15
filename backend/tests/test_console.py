"""Channel and video titles contain emoji and non-Latin scripts.

The Windows console defaults to cp1252, which cannot encode them, so printing a
title crashes with UnicodeEncodeError before any YouTube data is shown.
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]

EMOJI_TITLE = "Connected as テスト \U0001f600"


def run_on_a_cp1252_console(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND,
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_prints_non_ascii_titles_on_a_legacy_console():
    result = run_on_a_cp1252_console(
        "from app.console import use_utf8_stdout\n"
        "use_utf8_stdout()\n"
        f"print({EMOJI_TITLE!r})\n"
    )

    assert result.returncode == 0, result.stderr
    assert "Connected as" in result.stdout


def test_is_safe_to_call_more_than_once():
    result = run_on_a_cp1252_console(
        "from app.console import use_utf8_stdout\n"
        "use_utf8_stdout()\n"
        "use_utf8_stdout()\n"
        f"print({EMOJI_TITLE!r})\n"
    )

    assert result.returncode == 0, result.stderr
