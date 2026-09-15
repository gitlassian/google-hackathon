"""Run the extraction tool on local screenshots.

    .venv/bin/python cli.py test-images/yearbook-retention.png [more.png ...]
"""

import json
import sys
import time

from app.extractor import extract_retention_stats_from_file

if len(sys.argv) < 2:
    sys.exit(__doc__)

for path in sys.argv[1:]:
    started = time.perf_counter()
    stats = extract_retention_stats_from_file(path)
    elapsed = time.perf_counter() - started
    print(f"=== {path}  ({elapsed:.1f}s)")
    print(json.dumps(stats.model_dump(), indent=2))
