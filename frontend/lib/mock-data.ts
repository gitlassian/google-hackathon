import type { Analysis, Report } from "./types";

export const LOADING_STEPS = [
  "Uploading video…",
  "Watching the whole Short…",
  "Reading retention chart…",
  "Writing report…",
];

export const STREET_FOOD_REPORT: Report = {
  score: 58,
  verdict:
    "The hook is a still kitchen. People swipe at 0:03, before the food or the payoff ever appears.",
  extracted: {
    durationSec: 34,
    stayedToWatchPct: 41,
    avgViewDurationSec: 12.4,
    curve: [
      { t: 0, pct: 118 },
      { t: 1, pct: 111 },
      { t: 2, pct: 96 },
      { t: 3, pct: 72 },
      { t: 5, pct: 63 },
      { t: 8, pct: 57 },
      { t: 12, pct: 48 },
      { t: 18, pct: 46 },
      { t: 24, pct: 54 },
      { t: 30, pct: 67 },
      { t: 34, pct: 74 },
    ],
  },
  hook: {
    rating: "weak",
    firstThreeSeconds:
      "0:00 a quiet mid-shot of a stainless counter. 0:01 a hand enters with a knife, no face, no text. 0:02 the cook starts talking off-mic. 0:03 a title card fades in too small to read on a phone.",
    whyItWorksOrFails:
      "Nothing promises a payoff in the first frame. Audio is late, the text is unreadable, and the only motion is a hand — not the food. This is a classic first-three-seconds swipe-off.",
    rewrite:
      "Open on the crack of a baguette filling the frame, then the line: “I sold 200 of these in 4 hours — here’s the 12-second setup.” Cut to the stacked sandwiches by 0:02.",
  },
  dips: [
    {
      t: "0:03",
      dropPct: 26,
      onScreen: "Tiny title card over a still counter",
      cause: "Payoff still not visible; on-screen text is too small",
      fix: "First frame should be the finished sandwich, not the kitchen.",
    },
    {
      t: "0:12",
      dropPct: 9,
      onScreen: "Talking-head, no cut, repeating the same sentence",
      cause: "Pacing stall — four seconds with no visual change",
      fix: "Cut every 1.0–1.5s in the mid-section; show the process, don’t narrate it.",
    },
  ],
  stayedToWatch: {
    rating: "weak",
    explanation:
      "41% sits below the 50% “average” bar. Almost all of the loss is the 0:03 cliff, not the topic. Viewers who survive the hook actually hold through the loop — the content is fine, the opening is not.",
  },
  nextVideoRules: [
    "First frame is the finished food, filling the screen, with motion.",
    "Say the payoff in the first spoken second, on-mic.",
    "Phone-readable text: eight words max, high contrast, center-safe.",
    "Cut at least once a second until 0:08.",
    "End on a loop frame that matches the first frame.",
  ],
};

export const GYM_REPORT: Report = {
  score: 76,
  verdict:
    "The hook is strong — the fail clip does the work — but a 0:11 talking-head stall dumps the middle of the curve.",
  extracted: {
    durationSec: 28,
    stayedToWatchPct: 64,
    avgViewDurationSec: 16.8,
    curve: [
      { t: 0, pct: 124 },
      { t: 1, pct: 121 },
      { t: 2, pct: 118 },
      { t: 3, pct: 112 },
      { t: 6, pct: 98 },
      { t: 9, pct: 91 },
      { t: 11, pct: 71 },
      { t: 16, pct: 66 },
      { t: 21, pct: 69 },
      { t: 26, pct: 78 },
      { t: 28, pct: 81 },
    ],
  },
  hook: {
    rating: "strong",
    firstThreeSeconds:
      "0:00 barbell slips off a messy rack, loud clank. 0:01 face reaction, then a hard cut to the same lift done clean. 0:02 on-screen: “Fix this in one cue.”",
    whyItWorksOrFails:
      "The first frame is an event, not a setup. Sound hits immediately, the contrast cut promises a lesson, and the text is three words. This is why 0–3s holds above 110%.",
    rewrite:
      "Keep the fail. Add one spoken line over the clank: “This is why your deadlift rounds.” Then cut to the fix. Don’t wait until 0:11 to start teaching.",
  },
  dips: [
    {
      t: "0:11",
      dropPct: 20,
      onScreen: "Locked-off talking head, gym audio ducked, no overlay",
      cause: "After a kinetic hook, a still lecture feels like a different video",
      fix: "Teach over B-roll of the lift. Burn the cue as large text. Keep cutting.",
    },
  ],
  stayedToWatch: {
    rating: "ok",
    explanation:
      "64% is in the average band (50–70%). The hook is not the problem. The 0:11 cliff is a pacing break, and the ending loop recovers some of it — which is why the score is 76, not 50.",
  },
  nextVideoRules: [
    "Keep fail-then-fix as the first two shots.",
    "Never go more than 1.5s without a cut after a kinetic hook.",
    "Put the coaching cue on screen as text, not only in the voiceover.",
    "Return to the lift for the last 2 seconds so the loop matches the open.",
  ],
};

export const INITIAL_ANALYSES: Analysis[] = [
  {
    id: "a1",
    title: "Hook dies at 0:03",
    status: "ready",
    youtubeUrl: "https://www.youtube.com/shorts/example-street-food",
    videoName: "street-food.mp4",
    screenshotName: "studio-retention.png",
    screenshotPreview: null,
    videoPreview: null,
    report: STREET_FOOD_REPORT,
    messages: [],
    loadingStep: 0,
  },
  {
    id: "a2",
    title: "Gym reel — mid-video cliff",
    status: "ready",
    youtubeUrl: "https://www.youtube.com/shorts/example-gym-cue",
    videoName: "gym-cue.mp4",
    screenshotName: "studio-retention.png",
    screenshotPreview: null,
    videoPreview: null,
    report: GYM_REPORT,
    messages: [],
    loadingStep: 0,
  },
];

export function emptyAnalysis(id: string): Analysis {
  return {
    id,
    title: "New analysis",
    status: "draft",
    youtubeUrl: "",
    videoName: null,
    screenshotName: null,
    screenshotPreview: null,
    videoPreview: null,
    report: null,
    messages: [],
    loadingStep: 0,
  };
}

export function suggestionsFor(report: Report): string[] {
  const dip = report.dips[0]?.t ?? "0:03";
  return [
    `Why did people leave at ${dip}?`,
    "Give me 3 hook lines for this topic",
    "What should the first frame be?",
  ];
}
