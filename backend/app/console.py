"""Console output helpers for the CLI scripts."""

import sys


def use_utf8_stdout() -> None:
    """Make stdout/stderr able to print emoji and non-Latin scripts.

    YouTube titles routinely contain both, and the Windows console defaults to
    cp1252, which raises UnicodeEncodeError on them. `errors="replace"` keeps a
    terminal that genuinely cannot render a glyph from killing the whole run.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
