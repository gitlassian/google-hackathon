# Backend (FastAPI + Gemini)

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# put GEMINI_API_KEY=... in backend/.env
.venv/bin/fastapi dev app/main.py        # http://127.0.0.1:8000/docs
```

## Tools

- `POST /extract-retention` (multipart field `screenshot`) → stayed to watch, swiped away,
  average view duration, video duration, engaged views, and the retention curve as `[{t, pct}]`.
- CLI for testing: `.venv/bin/python cli.py test-images/yearbook-retention.png`
