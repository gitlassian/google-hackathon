# Shorts Retention Coach — Hackathon Plan

## 1. Confirmed intent

- **Outcome:** A web tool where a creator submits a YouTube Short (link and/or upload) plus a YouTube Studio retention screenshot. Gemini watches the full video, reads the chart, returns a scored coaching report, then answers follow-up questions in a chat that keeps the video in context.
- **User:** Shorts creators analyzing their own published videos.
- **Why:** Stats only exist after posting, so the value is learning what to change in the *next* Short, not re-editing this one.
- **Success:** The report names the exact second the hook loses people and why, ties each retention dip to what is on screen at that moment, explains the stayed-to-watch number, and gives 3–5 rules for the next video. A judge should get it in ten seconds.
- **Constraint:** One Gemini prompt does the whole analysis. Public links go straight to Gemini as a URL; uploads go through the Files API. No auth, no database, no channel history.
- **Out of scope:** Long-form videos, YouTube Analytics API, zero-view diagnosis beyond hook/title/thumbnail advice, re-editing tools.

## 2. What Gemini can do (verified 2026-09-15)

| Fact | Detail |
|---|---|
| Model | `gemini-3.8-flash` (latest stable Flash, supports agentic + static video). Fallback: `gemini-3.1-pro-preview`. |
| YouTube link | Pass `{type:"video", uri:"https://youtube.com/..."}` directly. **Public videos only** (not unlisted/private). Free tier: 8 h of YouTube video/day. |
| Uploaded file | Files API: upload, poll until `state == "ACTIVE"`, then pass `uri` + `mime_type`. 2 GB free tier. |
| Sampling | Static mode: 1 fps, audio included, timestamps every second. Perfect for a <60 s Short. Use static, not agentic (agentic is for long videos). |
| Timestamps | Reference in prompt as `MM:SS`. Model returns them the same way. |
| Chat | Interactions API is stateful: pass `previous_interaction_id` and the video stays in context. No re-upload per turn. |
| Image | Retention screenshot goes in as an image part in the same request. |

Docs: https://ai.google.dev/gemini-api/docs/video-understanding

## 3. Architecture

```
Browser (Next.js app)
  │  POST /api/analyze   { youtubeUrl? , videoFile? , screenshotFile }
  ▼
API route (Node)
  ├─ resolve video source
  │    ├─ public YouTube URL  → pass URL straight to Gemini
  │    ├─ uploaded file       → Files API upload → poll ACTIVE
  │    └─ unlisted/private URL → yt-dlp download → Files API   (fallback, do last)
  ├─ build ONE prompt: system rules + screenshot + video + JSON schema
  ├─ call gemini-3.8-flash (static processing, response_schema = Report)
  └─ return { report, interactionId }

  POST /api/chat  { interactionId, message }  → previous_interaction_id → answer
```

Stack: Next.js (App Router) + `@google/genai` SDK + Tailwind. One repo, `pnpm dev`, deploy to Vercel or run locally for demo. No DB: `interactionId` lives in the browser tab.

## 4. The single analysis prompt

Inputs to the model, in order:
1. Retention screenshot (image)
2. The video (URL or file URI)
3. Text prompt

Prompt skeleton (`lib/prompt.ts`):

```
You are a YouTube Shorts retention coach. You are given (1) a screenshot of
YouTube Studio's Audience Retention panel and (2) the full Short.

STEP 1 — READ THE SCREENSHOT. Extract: video duration from the x-axis,
"Stayed to watch" %, "Average view duration", and the curve as ~10 points
(timestamp MM:SS → %). Shorts curves start above 100% because of rewatches/loops.

STEP 2 — WATCH THE WHOLE VIDEO with audio. Note what is on screen and said
at every second for the first 5 s, and at every dip you found in step 1.

STEP 3 — DIAGNOSE using these Shorts benchmarks:
- Stayed to watch: ≥70% strong, 50–70% average, <50% weak (viewers swipe in first 3 s → hook problem)
- Hook window is 0–3 s. A hook fails if: payoff not stated, slow first frame, text unreadable,
  no motion, generic opening line, audio starts late.
- A drop of >15 percentage points within 3 s is a "cliff": tie it to the exact on-screen event.
- Ending above ~60% with a loop = good; a flat mid-section = pacing, not content, is the issue.
- Zero/low views with OK retention = distribution problem (title/first frame/topic), not editing.

STEP 4 — OUTPUT strictly as the JSON schema. Timestamps as MM:SS. Every claim
must cite what is visible/audible at that timestamp. Tips must be actionable
for the NEXT video, not re-edits.
```

Response schema (`lib/schema.ts`), enforced via `response_schema`:

```ts
{
  score: number,                     // 0–100
  verdict: string,                   // one sentence
  extracted: { durationSec, stayedToWatchPct, avgViewDurationSec, curve: [{t, pct}] },
  hook: { rating: "strong"|"ok"|"weak", firstThreeSeconds: string, whyItWorksOrFails: string, rewrite: string },
  dips: [{ t: "MM:SS", dropPct: number, onScreen: string, cause: string, fix: string }],
  stayedToWatch: { rating, explanation },
  nextVideoRules: string[],          // 3–5
  distributionNote?: string          // only if views are near zero
}
```

Chat turns: same interaction, system reminder "answer about this video; cite MM:SS".

## 5. UI (3 screens)

1. **Input:** paste link OR drop video; drop screenshot (required). Big "Analyze" button. Validate: link must be youtube.com/shorts or watch URL; screenshot must be an image.
2. **Loading:** staged progress text ("Uploading video… Watching all 33 s… Reading retention chart… Writing report") so the 10–30 s wait feels alive.
3. **Report:**
   - Score ring + one-line verdict
   - Hook card (0–3 s): rating chip, what happens, why, suggested rewrite
   - Retention timeline: video player on the left, extracted curve on the right, dip markers clickable → seeks player to that second
   - Stayed-to-watch card
   - "Rules for your next Short" list
   - Chat drawer at the bottom, prefilled suggestions ("Why did people leave at 0:06?", "Give me 3 hook lines for this topic")

## 6. Work split (3 tracks, run in parallel)

| Track | Owner | Deliverables |
|---|---|---|
| A. Gemini core | most experienced (you) | `lib/gemini.ts` (URL path, Files API path, polling), prompt + schema, `/api/analyze`, `/api/chat`. Test on 5 of your real screenshots + their videos first, from a script, before any UI exists. |
| B. Frontend | teammate 2 | Input screen, loading states, report layout, chat drawer, player seek on dip click. Build against a mocked `report.json` from track A on day 1. |
| C. Data + demo | teammate 3 | Collect 5–8 public Shorts with screenshots that show distinct problems (bad hook, mid cliff, flat, great). Write the demo script. Handle yt-dlp fallback if time allows. Slides. |

## 7. Timeline (assume ~24 h build)

| Hour | Milestone |
|---|---|
| 0–2 | Repo scaffold, API key in `.env.local`, script that sends one URL + one screenshot and prints raw Gemini output. **This is the go/no-go check.** |
| 2–6 | Prompt iteration on 5 real examples until timestamps and causes are right. JSON schema locked. Frontend built on mock. |
| 6–10 | Wire real API to UI. Files API upload path. Chat endpoint. |
| 10–14 | Retention timeline + player seek. Loading states. Error handling (private video, bad screenshot, quota). |
| 14–18 | Polish, run the full demo 5 times end to end, cache one result as a fallback if API dies on stage. |
| 18–24 | Slides, README, stretch goals only if everything above is green. |

## 8. Risks and mitigations

- **Link is unlisted/private** → clear error + "upload the file instead"; yt-dlp fallback only if time.
- **Gemini misreads the curve** → the prompt forces it to output the extracted curve first; we show it next to the screenshot so errors are visible. Pass duration explicitly if the video was uploaded (we know it from ffprobe/the file).
- **Quota / rate limit during demo** → paid tier key, plus one cached report JSON to replay.
- **Latency** → Shorts are <60 s, static mode, Flash model: expect 10–30 s. Staged loading text.
- **Malformed JSON** → `response_schema` + one retry.
- **Video with no retention screenshot** → still allowed: skip dips, report hook + distribution advice only.

## 9. Stretch (only after demo is solid)

- Overlay the extracted retention curve on the video scrubber.
- Compare two Shorts from the same channel to find a repeating hook pattern.
- Long-form support with agentic processing mode.
- Auto-generate 3 alternative first frames/hook lines (Gemini image output).
