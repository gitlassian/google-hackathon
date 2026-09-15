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

## Does retention work for Shorts? Yes — verified

Google's docs never say whether the audience retention report covers Shorts. It does: 100 rows
for a Short, same as long-form, with `relativeRetentionPerformance` and `audienceType==ORGANIC`
both working. That is why the Analytics API is the primary retention source and the screenshot
is the fallback.

`youtube_probe.py` is what established this, and is kept because it re-checks the query shapes
against a live channel:

```bash
.venv/Scripts/python youtube_probe.py
.venv/Scripts/python youtube_probe.py --start 2025-01-01 --end 2026-09-15
.venv/Scripts/python youtube_probe.py --video VIDEO_ID
```

| Variant | Adds | Result |
|---|---|---|
| A | `audienceWatchRatio` only | 100 rows |
| B | `+ relativeRetentionPerformance` | 100 rows |
| C | `+ audienceType==ORGANIC` | 100 rows |
| D | `startedWatching` / `stoppedWatching` / `totalSegmentImpressions` | 100 rows |

Variant D looked empty on first run. That was the rolling-window bug, not a missing metric —
over full history it returns all 100 rows, and those counters are what `stayed_to_watch_pct` is
computed from.

## Asking Gemini about the channel

`POST /channel/chat` `{"message": "...", "interaction_id": "..."}` — Gemini answers questions
about the connected channel by calling the YouTube tools itself, rather than being handed a
fixed payload. Pass the previous answer's `interaction_id` to continue the conversation.

```bash
curl -s localhost:8000/channel/chat -H 'Content-Type: application/json' \
  -d '{"message":"Which of my Shorts has the worst hook, and why?"}'
```

The response carries `tool_calls`, a trace of what it fetched — worth showing in a demo.

Six tools, in `app/youtube_tools.py`: `list_my_shorts`, `get_video_stats`,
`get_retention_curve`, `get_traffic_sources`, `get_channel_summary`, `resolve_video`. Keep the
list small; large tool lists measurably hurt selection accuracy.

### Two things that will bite you here

- **A tool result must be a JSON string.** Handing `function_result.result` a raw list gets it
  silently discarded, and the model then **invents plausible data** rather than saying it
  received none. Verified live: a list produced a confident answer about videos that do not
  exist; the identical payload as a string produced the correct answer. `_serialize()` in
  `app/channel_agent.py` exists solely for this.
- **Tool failures are returned to the model, not raised.** `run_tool` catches everything and
  returns `is_error: true`, so "you don't own that video" is something the model can explain
  instead of a 500 that kills the conversation.

The retention curve is thinned to ~12 points before it reaches the model. Sent raw, 100 points
cost roughly 2k tokens per call for a shape a dozen conveys.

## Checking it still works

```bash
.venv/Scripts/python youtube_check.py
```

Walks every facade method against the connected channel and flags any field that
comes back null, empty or zero. Run it before a demo.

## Tests

```bash
.venv/Scripts/python -m pytest tests/ -q
```

No network and no credentials — these cover the pure functions only (URL/ID resolution,
ISO-8601 durations, retention rows → curve, drop detection, stayed-to-watch derivation).

## Using it from other backend code

```python
from app.youtube import YouTubeService

yt = YouTubeService()
if yt.is_connected():
    for short in yt.list_my_shorts(limit=10):
        print(short.video_id, short.views, short.stayed_to_watch_pct)

    stats = yt.get_retention_stats("https://www.youtube.com/shorts/VIDEO_ID")
    stats.source              # "analytics_api"
    stats.retention_curve     # 100 CurvePoints
```

Import from `app.youtube` and nothing deeper. Everything raises subclasses of `YouTubeError`.

## Endpoints

| Route | Purpose |
|---|---|
| `POST /retention` | **Start here.** Form `url` and/or `screenshot`; picks the best source |
| `POST /extract-retention` | Screenshot only |
| `GET /youtube/status` | Is a channel connected, and which |
| `GET /youtube/auth/start` → `/auth/callback` | Browser OAuth |
| `GET /youtube/summary` | Channel totals plus a per-content-type breakdown |
| `GET /youtube/shorts` · `/youtube/videos` | Per-video performance, best first |
| `GET /youtube/videos/{id}/retention` | `RetentionStats` from the API |
| `GET /youtube/videos/{id}/stats` · `/timeseries` · `/traffic-sources` · `/metadata` | |
| `GET /youtube/resolve?url=…` | URL → video ID |

Path parameters take a bare video ID. Pass full URLs via `?url=` or `POST /retention`.

## Module layout

```
app/
  main.py          app setup only
  console.py       UTF-8 stdout for the CLI scripts
  extractor.py     Gemini: screenshot -> RetentionStats
  retention.py     curve maths shared by both sources
  schemas.py       RetentionStats, CurvePoint, Drop
  routers/
    retention.py   POST /retention, POST /extract-retention
    youtube.py     everything under /youtube
  youtube/
    service.py     YouTubeService — the facade to import
    analytics_api.py  Analytics v2; every query shape here is verified
    data_api.py    Data v3 metadata
    auth.py        OAuth: credential stores, CLI flow, web flow
    config.py      YOUTUBE_* settings (never fails at import)
    errors.py      NotAuthenticated, NotChannelOwner, QuotaExceeded, NoDataAvailable
    mapping.py     Analytics rows -> RetentionStats
    models.py      VideoMetadata, ChannelMetadata, VideoPerformance, ...
    parsing.py     URL/ID resolution, ISO-8601 durations
```

### Notes for whoever builds on this

Query shapes, established against a live channel. Several contradict the reference docs, so
trust this list over <https://developers.google.com/youtube/analytics/dimensions>:

- **`creatorContentType` IS a valid filter**, despite the docs calling it dimension-only. It
  only accepts **lowercase**: `filters=creatorContentType==shorts` works, `==SHORTS` fails with
  `Invalid value (SHORTS)`. Returned values are lowercase too.
- **`video` and `creatorContentType` cannot both be dimensions.** Rejected in either order with
  "The query is not supported", so rows cannot be labelled with their content type. Filter
  instead. `group_by_content_type` is only for a `dimensions=creatorContentType` report.
- **A `dimensions=video` report requires both `sort` and `maxResults`.** Omitting them gives the
  same unhelpful "query is not supported".
- `elapsedVideoTimeRatio` runs `0.01 → 1.00`. **There is no `t=0` row.** The curve starts at 1%
  of the video, and `curve_from_retention_rows` deliberately does not fabricate a zero point.
- The `video` filter on the retention report accepts exactly one ID — one HTTP call per video.
- `startedWatching`, `stoppedWatching` and `totalSegmentImpressions` return **no rows**. Studio's
  "Stayed to watch" is not an API metric either; `derive_stayed_to_watch_pct` approximates it as
  `engagedViews / views` and says so in `notes`. Do not present it as YouTube's own figure.
- **Queries default to the whole history (`2008-07-01` → today), and should.** A rolling window
  silently truncates. On the test channel a two-year window reported 254 views against 9150
  lifetime, and returned a retention curve for **5 of 13** videos instead of all 13 — the other
  eight simply had their watch time before the window. Pass `start`/`end` to narrow deliberately.
- **Studio's "Stayed to watch" cannot be reproduced from the API. Do not try again.** Two
  derivations were built and both were wrong, each after looking convincing on a single video:

  | Derivation | `i-8TOGtJxTc` (Studio 74.4%) | `seIjJBsdCRc` (Studio 48.1%) |
  |---|---|---|
  | `engagedViews / views` | 33.3% | — |
  | viewers remaining at 1.0s | 77.3% ✓ | **94.2%** ✗ |

  It is not a fixed time cutoff: Studio's swipe figure is reached at 1.5s on one of those videos
  and 6.0s on the other. `stayed_to_watch_pct` and `swiped_away_pct` are therefore **always null**
  on the API path. Studio's number is real and useful — read it off a screenshot, which is what
  the Gemini extractor is for.
- **Use `viewers_remaining` instead.** Share of viewers still there at 1, 3 and 5 seconds, from
  `startedWatching` / `stoppedWatching`. A plain fact, correctly labelled, never presented as
  Studio's metric. Absent on low-view videos, where YouTube withholds the counters.
- **`startedWatching` / `stoppedWatching` return HTTP 500 if requested alone** — pair them with
  `audienceWatchRatio`. They are also suppressed below some view threshold, and asking for them
  takes the *whole* result down: a 57-view video returns 100 rows without them and 0 rows with.
  `AnalyticsApiClient.retention` falls back to `SAFE_RETENTION_METRICS` for exactly this.
- **The curve itself is exact** and matched Studio's chart on both videos checked (42.47 vs 42%,
  68.02 vs the plotted endpoint). Trust the curve; distrust any summary number derived from it.
- **Shorts loop, so watch-time metrics exceed 100%.** A `PT57S` Short reports
  `averageViewPercentage` 159% and `audienceWatchRatio` 2.29 at the first sample over a narrow
  window. Nothing downstream may treat that as an error.
- **Day-level `averageViewDuration` can be nonsense.** One day on the test channel reported 854 s
  for a 57 s video, and disagreed with `estimatedMinutesWatched / views` on the same row. Use the
  video-level figure, not the daily one.
- Per-video `likes` can be **negative** over a date range — it is the net change in that window,
  not a total. The channel total came back as -50 while the public like count was 368.
- Data API quota is 10,000 units/day. `videos.list` / `channels.list` / `playlistItems.list`
  cost 1 unit; `search.list` costs 100 — walk the uploads playlist instead.
- The Google client is **synchronous**. Routes calling it must be `def`, not `async def`, so
  FastAPI runs them in a threadpool.
- Titles contain emoji and non-Latin scripts. CLI scripts must call `app.console.use_utf8_stdout()`
  or they crash on the Windows cp1252 console before printing anything.
