# Backend (FastAPI + Gemini + YouTube)

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
.venv/bin/pip install -r requirements.txt                 # macOS / Linux

# put GEMINI_API_KEY=... in backend/.env
.venv/Scripts/fastapi dev app/main.py     # http://127.0.0.1:8000/docs
```

Paths below use `.venv/Scripts/python` (Windows); substitute `.venv/bin/python` elsewhere.

## Two sources of retention data

| Source | Works for | Accuracy |
|---|---|---|
| Screenshot (Gemini) | any video, no login | a model reading a chart — carries `reading_confidence` |
| YouTube Analytics API | videos on a channel you own | exact, `reading_confidence = 1.0` |

Both return the same `RetentionStats`, distinguished by its `source` field, so consumers do
not care which one produced the numbers.

## Screenshot path

- `POST /extract-retention` (multipart field `screenshot`) → stayed to watch, swiped away,
  average view duration, video duration, engaged views, and the retention curve as `[{t, pct}]`.
- CLI: `.venv/Scripts/python cli.py test-images/yearbook-retention.png`

## YouTube path — one-time setup

You need your own OAuth client. It takes about five minutes and no billing account.

1. **Create a project** — <https://console.cloud.google.com/projectcreate>.
   Confirm the project picker in the top bar switched to it before continuing.

2. **Enable both APIs** (the second one is the one that matters; it is easy to miss):
   - [YouTube Data API v3](https://console.cloud.google.com/apis/library/youtube.googleapis.com)
   - [YouTube Analytics API](https://console.cloud.google.com/apis/library/youtubeanalytics.googleapis.com)

3. **Consent screen** — <https://console.cloud.google.com/auth/overview> → *Get started*.
   App name and support email are yours to pick; Audience must be **External**.

4. **Add yourself as a test user** — <https://console.cloud.google.com/auth/audience> →
   *Test users* → the Google account **that owns the YouTube channel**.
   Skipping this fails later with a bare `access_denied`.

5. **Create the client** — <https://console.cloud.google.com/auth/clients> → *Create client*
   → application type **Desktop app** → *Download JSON*. Save it as `backend/client_secret.json`
   (gitignored).

Then connect the channel:

```bash
.venv/Scripts/python connect_youtube.py            # opens a browser once
.venv/Scripts/python connect_youtube.py --status   # who am I connected as?
.venv/Scripts/python connect_youtube.py --forget   # drop the stored token
```

Expect these:

- **"Google hasn't verified this app"** → *Advanced* → *Go to … (unsafe)*. Normal in testing mode.
- **Brand Account channels** show an account picker during consent. Pick the channel, not your
  personal account, or `mine=True` comes back empty.
- **Testing-mode refresh tokens expire after 7 days.** Rerun `connect_youtube.py`.

Credentials land in `backend/.youtube-token.json`. Override any path via `backend/.env`:
`YOUTUBE_CLIENT_SECRETS_FILE`, `YOUTUBE_TOKEN_FILE`, `YOUTUBE_API_KEY`, `YOUTUBE_OAUTH_REDIRECT_URI`.

## Open question: does Shorts retention exist in the API?

Google's docs never say whether the audience retention report returns data for Shorts. Studio
shows the curve, but that is not evidence about the API, and the rest of the YouTube module
depends on the answer. Settle it first:

```bash
.venv/Scripts/python youtube_probe.py
.venv/Scripts/python youtube_probe.py --start 2025-01-01 --end 2026-09-15
.venv/Scripts/python youtube_probe.py --video VIDEO_ID
```

It prints your channel, a `SHORTS` / `VIDEO_ON_DEMAND` breakdown, and the row count for four
escalating retention queries against your top Short **and** a long-form control:

| Variant | Adds |
|---|---|
| A | `audienceWatchRatio` only — the minimum that can work |
| B | `relativeRetentionPerformance` (suspected to be empty on very short videos) |
| C | `audienceType==ORGANIC` (the commonly copy-pasted filter) |
| D | `startedWatching` / `stoppedWatching` / `totalSegmentImpressions` |

**Reading the result:** ~100 rows for the Short under variant A means the API path becomes the
primary retention source. Empty for the Short but fine for the control means Shorts retention
is not exposed and the screenshot stays primary.

## Tests

```bash
.venv/Scripts/python -m pytest tests/ -q
```

No network and no credentials — these cover the pure functions only (URL/ID resolution,
ISO-8601 durations, retention rows → curve, drop detection, stayed-to-watch derivation).

## Module layout

```
app/
  main.py          FastAPI app
  extractor.py     Gemini: screenshot -> RetentionStats
  retention.py     curve maths shared by both sources
  schemas.py       RetentionStats, CurvePoint, Drop
  youtube/
    auth.py        OAuth: credential stores, CLI flow, web flow
    config.py      YOUTUBE_* settings (never fails at import)
    errors.py      NotAuthenticated, NotChannelOwner, QuotaExceeded, NoDataAvailable
    mapping.py     Analytics rows -> RetentionStats
    parsing.py     URL/ID resolution, ISO-8601 durations
```

### Notes for whoever builds on this

- `creatorContentType` (`SHORTS`, `VIDEO_ON_DEMAND`, …) is **dimension-only**. YouTube rejects
  `filters=creatorContentType==SHORTS`; request it as a dimension and split client-side.
- `elapsedVideoTimeRatio` runs `0.01 → 1.00`. **There is no `t=0` row.** The curve starts at 1%
  of the video, and `curve_from_retention_rows` deliberately does not fabricate a zero point.
- The `video` filter on the retention report accepts exactly one ID — one HTTP call per video.
- Studio's "Stayed to watch" is not an API metric. `derive_stayed_to_watch_pct` approximates it
  as `engagedViews / views` and records that in `notes`; do not present it as YouTube's own figure.
- Data API quota is 10,000 units/day. `videos.list` / `channels.list` / `playlistItems.list`
  cost 1 unit; `search.list` costs 100 — walk the uploads playlist instead.
- The Google client is **synchronous**. Routes calling it must be `def`, not `async def`, so
  FastAPI runs them in a threadpool.
