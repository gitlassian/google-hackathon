import type { RetentionStats } from "./types";

export const EXTRACT_STATS_PROMPT = `You are reading a screenshot of YouTube Studio's Audience Retention panel for a YouTube Short.

Extract every number you can see. Do not invent values you cannot read — use null.

Rules:
- durationSec comes from the x-axis end (often 0:15–0:60).
- stayedToWatchPct is the "Stayed to watch" percentage.
- avgViewDurationSec is "Average view duration", converted to seconds.
- Sample the curve as 8–16 points. t is seconds from 0. pct is the y-value.
- Shorts curves often start ABOVE 100% because of rewatches/loops. Keep that.
- A drop of more than 15 points inside 3 seconds is a cliff — mention it in chartNotes.
- source must be "screenshot".`;

export function analyzePrompt(stats: RetentionStats): string {
  const statsJson = JSON.stringify(stats, null, 2);
  return `You are a YouTube Shorts retention coach.

You are given:
1) Structured retention stats (already extracted — trust these numbers, do not re-guess the chart).
2) The full Short (video), with audio. Watch every second of the first 5 seconds, and every dip in the curve.

RETENTION STATS:
${statsJson}

DIAGNOSE with these benchmarks:
- Stayed to watch: ≥70% strong, 50–70% ok, <50% weak (swipe in first 3 s → hook problem).
- Hook window is 0–3 s. A hook fails if: payoff not stated, slow first frame, text unreadable, no motion, generic opening line, audio starts late.
- A drop of >15 percentage points within 3 s is a "cliff": tie it to the exact on-screen event at that timestamp.
- Ending above ~60% with a loop = good; a flat mid-section = pacing, not content.
- Zero/low views with OK retention = distribution (title / first frame / topic), not editing.

OUTPUT the JSON schema. Timestamps in dips as MM:SS.
Every claim must cite what is visible or audible at that timestamp.
Tips must be for the NEXT video, not a recut of this one.
Copy durationSec, stayedToWatchPct, avgViewDurationSec, and curve into extracted.
If stayedToWatchPct or avgViewDurationSec is null, estimate from the curve and say so in the explanation.`;
}

export const CHAT_SYSTEM = `Answer only about this Short. Cite timestamps as MM:SS. Stay in English. Do not recut this video — coach the next one.`;
