/**
 * JSON Schemas sent to Gemini as response_format.
 *
 * Edit RETENTION_STATS_SCHEMA when you want more (or fewer) Studio numbers
 * pulled from the screenshot. The coaching prompt consumes whatever this
 * object contains — do not silently drop fields in gemini.ts.
 */

export const RETENTION_STATS_SCHEMA = {
  type: "object",
  properties: {
    source: {
      type: "string",
      enum: ["screenshot", "youtube_api", "none"],
      description: "Where these numbers came from.",
    },
    durationSec: {
      type: "number",
      description: "Video length in seconds, from the x-axis of the chart.",
    },
    stayedToWatchPct: {
      type: ["number", "null"],
      description: "YouTube Studio 'Stayed to watch' percentage. Null if not visible.",
    },
    avgViewDurationSec: {
      type: ["number", "null"],
      description: "Average view duration in seconds. Null if not visible.",
    },
    views: {
      type: ["number", "null"],
      description: "View count if printed on the screenshot, else null.",
    },
    impressions: {
      type: ["number", "null"],
      description: "Impressions if printed on the screenshot, else null.",
    },
    swipeAwayPct: {
      type: ["number", "null"],
      description: "Swipe-away / skip rate if printed, else null.",
    },
    curve: {
      type: "array",
      description:
        "8–16 points along the audience-retention curve. t is seconds from start. pct can exceed 100 on Shorts because of rewatches.",
      items: {
        type: "object",
        properties: {
          t: {
            type: "number",
            description: "Seconds from the start of the video.",
          },
          pct: {
            type: "number",
            description: "Retention percent at that second.",
          },
        },
        required: ["t", "pct"],
      },
    },
    chartNotes: {
      type: "string",
      description:
        "Anything else readable on the panel: axis labels, obvious cliffs, loop bump at the end.",
    },
  },
  required: [
    "source",
    "durationSec",
    "stayedToWatchPct",
    "avgViewDurationSec",
    "views",
    "impressions",
    "swipeAwayPct",
    "curve",
    "chartNotes",
  ],
} as const;

export const REPORT_SCHEMA = {
  type: "object",
  properties: {
    score: {
      type: "integer",
      minimum: 0,
      maximum: 100,
      description: "Overall coaching score for this Short.",
    },
    verdict: {
      type: "string",
      description: "One sentence a judge can read in two seconds.",
    },
    extracted: {
      type: "object",
      description: "Echo of the retention stats used for this report.",
      properties: {
        durationSec: { type: "number" },
        stayedToWatchPct: { type: "number" },
        avgViewDurationSec: { type: "number" },
        curve: {
          type: "array",
          items: {
            type: "object",
            properties: {
              t: { type: "number" },
              pct: { type: "number" },
            },
            required: ["t", "pct"],
          },
        },
      },
      required: [
        "durationSec",
        "stayedToWatchPct",
        "avgViewDurationSec",
        "curve",
      ],
    },
    hook: {
      type: "object",
      properties: {
        rating: { type: "string", enum: ["strong", "ok", "weak"] },
        firstThreeSeconds: {
          type: "string",
          description: "What is on screen and said at 0:00, 0:01, 0:02, 0:03.",
        },
        whyItWorksOrFails: { type: "string" },
        rewrite: {
          type: "string",
          description: "Spoken + visual hook for the NEXT video, not a recut.",
        },
      },
      required: [
        "rating",
        "firstThreeSeconds",
        "whyItWorksOrFails",
        "rewrite",
      ],
    },
    dips: {
      type: "array",
      items: {
        type: "object",
        properties: {
          t: {
            type: "string",
            description: "Timestamp as MM:SS.",
          },
          dropPct: { type: "number" },
          onScreen: { type: "string" },
          cause: { type: "string" },
          fix: { type: "string" },
        },
        required: ["t", "dropPct", "onScreen", "cause", "fix"],
      },
    },
    stayedToWatch: {
      type: "object",
      properties: {
        rating: { type: "string", enum: ["strong", "ok", "weak"] },
        explanation: { type: "string" },
      },
      required: ["rating", "explanation"],
    },
    nextVideoRules: {
      type: "array",
      minItems: 3,
      maxItems: 5,
      items: { type: "string" },
    },
    distributionNote: {
      type: "string",
      description: "Only if views look near zero. Otherwise omit or empty.",
    },
  },
  required: [
    "score",
    "verdict",
    "extracted",
    "hook",
    "dips",
    "stayedToWatch",
    "nextVideoRules",
  ],
} as const;
