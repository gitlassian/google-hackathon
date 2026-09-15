import { GoogleGenAI } from "@google/genai";
import { GEMINI_FALLBACK_MODEL, GEMINI_MODEL } from "./constants";
import { analyzePrompt, CHAT_SYSTEM, EXTRACT_STATS_PROMPT } from "./prompt";
import { REPORT_SCHEMA, RETENTION_STATS_SCHEMA } from "./schema";
import { parseTimestamp } from "./format";
import type { Report, RetentionStats } from "./types";

export function createClient(apiKey: string) {
  return new GoogleGenAI({ apiKey });
}

type InteractionLike = {
  id?: string;
  output_text?: string;
  outputs?: Array<{ text?: string }>;
};

function interactionText(interaction: InteractionLike): string {
  if (interaction.output_text?.trim()) return interaction.output_text;
  const last = interaction.outputs?.at(-1);
  return last?.text ?? "";
}

function parseJsonObject(raw: string): unknown {
  const trimmed = raw
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "");
  return JSON.parse(trimmed);
}

type ContentPart =
  | { type: "text"; text: string }
  | { type: "image"; data: string; mime_type: string }
  | {
      type: "video";
      uri: string;
      mime_type?: string;
      processing?: { type: "static"; fps: number } | "static";
    };

type CreateBody = {
  input: string | ContentPart[];
  system_instruction?: string;
  previous_interaction_id?: string;
  response_format?: {
    type: "text";
    mime_type: "application/json";
    schema: object;
  };
  generation_config?: { temperature?: number };
};

async function createWithFallback(ai: GoogleGenAI, params: CreateBody) {
  const call = (model: string) =>
    ai.interactions.create({
      model,
      ...params,
    } as Parameters<GoogleGenAI["interactions"]["create"]>[0]);
  try {
    return await call(GEMINI_MODEL);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    if (!/not found|NOT_FOUND|invalid model/i.test(message)) throw err;
    return await call(GEMINI_FALLBACK_MODEL);
  }
}

export async function uploadMedia(
  ai: GoogleGenAI,
  file: File,
  fallbackMime: string,
): Promise<{ uri: string; mimeType: string }> {
  const mimeType = file.type || fallbackMime;
  const buffer = Buffer.from(await file.arrayBuffer());
  const blob = new Blob([buffer], { type: mimeType });
  const uploaded = await ai.files.upload({
    file: blob,
    config: { mimeType, displayName: file.name },
  });

  let current = uploaded;
  const name = current.name;
  if (!name) {
    throw new Error("Gemini Files API did not return a file name.");
  }

  for (let i = 0; i < 40; i++) {
    const state = String(current.state ?? "");
    if (state === "ACTIVE" || state === "SUCCEEDED") {
      const uri = current.uri;
      if (!uri) throw new Error("Gemini file is active but has no uri.");
      return { uri, mimeType: current.mimeType || mimeType };
    }
    if (state === "FAILED") {
      throw new Error("Gemini failed to process the uploaded file.");
    }
    await new Promise((r) => setTimeout(r, 1500));
    current = await ai.files.get({ name });
  }
  throw new Error("Timed out waiting for Gemini to process the upload.");
}

async function fileToInlineImage(file: File) {
  const buffer = Buffer.from(await file.arrayBuffer());
  return {
    type: "image" as const,
    data: buffer.toString("base64"),
    mime_type: file.type || "image/png",
  };
}

export async function extractStatsFromScreenshot(
  ai: GoogleGenAI,
  screenshot: File,
): Promise<RetentionStats> {
  const image = await fileToInlineImage(screenshot);
  const interaction = (await createWithFallback(ai, {
    input: [image, { type: "text", text: EXTRACT_STATS_PROMPT }],
    response_format: {
      type: "text",
      mime_type: "application/json",
      schema: RETENTION_STATS_SCHEMA,
    },
    generation_config: { temperature: 0.1 },
  })) as InteractionLike;

  const parsed = parseJsonObject(interactionText(interaction)) as RetentionStats;
  return normalizeStats(parsed, "screenshot");
}

type VideoInput =
  | { kind: "youtube"; url: string }
  | { kind: "file"; uri: string; mimeType: string };

export async function analyzeVideo(options: {
  ai: GoogleGenAI;
  video: VideoInput;
  stats: RetentionStats;
  screenshot?: File;
}): Promise<{ report: Report; interactionId: string }> {
  const input: ContentPart[] = [];

  if (options.screenshot) {
    input.push(await fileToInlineImage(options.screenshot));
  }

  if (options.video.kind === "youtube") {
    input.push({
      type: "video",
      uri: options.video.url,
      processing: { type: "static", fps: 1 },
    });
  } else {
    input.push({
      type: "video",
      uri: options.video.uri,
      mime_type: options.video.mimeType,
      processing: { type: "static", fps: 1 },
    });
  }

  input.push({ type: "text", text: analyzePrompt(options.stats) });

  const interaction = (await createWithFallback(options.ai, {
    input,
    system_instruction: CHAT_SYSTEM,
    response_format: {
      type: "text",
      mime_type: "application/json",
      schema: REPORT_SCHEMA,
    },
    generation_config: { temperature: 0.1 },
  })) as InteractionLike;

  const id = interaction.id;
  if (!id) throw new Error("Gemini did not return an interaction id.");
  const parsed = parseJsonObject(interactionText(interaction));
  return { report: normalizeReport(parsed, options.stats), interactionId: id };
}

export async function continueChat(options: {
  ai: GoogleGenAI;
  interactionId: string;
  message: string;
}): Promise<{ reply: string; interactionId: string }> {
  const interaction = (await createWithFallback(options.ai, {
    previous_interaction_id: options.interactionId,
    system_instruction: CHAT_SYSTEM,
    input: options.message,
    generation_config: { temperature: 0.2 },
  })) as InteractionLike;

  const id = interaction.id ?? options.interactionId;
  const reply = interactionText(interaction).trim();
  if (!reply) throw new Error("Gemini returned an empty chat reply.");
  return { reply, interactionId: id };
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.includes(":")) return parseTimestamp(value);
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function asNullableNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const n = asNumber(value, Number.NaN);
  return Number.isFinite(n) ? n : null;
}

export function normalizeStats(
  raw: Partial<RetentionStats> | null | undefined,
  source: RetentionStats["source"],
): RetentionStats {
  const curve = Array.isArray(raw?.curve)
    ? raw.curve
        .map((p) => ({
          t: asNumber((p as { t?: unknown }).t, 0),
          pct: asNumber((p as { pct?: unknown }).pct, 0),
        }))
        .sort((a, b) => a.t - b.t)
    : [];

  return {
    source: raw?.source ?? source,
    durationSec: asNumber(raw?.durationSec, curve.at(-1)?.t ?? 0),
    stayedToWatchPct: asNullableNumber(raw?.stayedToWatchPct),
    avgViewDurationSec: asNullableNumber(raw?.avgViewDurationSec),
    views: asNullableNumber(raw?.views),
    impressions: asNullableNumber(raw?.impressions),
    swipeAwayPct: asNullableNumber(raw?.swipeAwayPct),
    curve,
    chartNotes: typeof raw?.chartNotes === "string" ? raw.chartNotes : "",
  };
}

export function emptyStats(): RetentionStats {
  return {
    source: "none",
    durationSec: 0,
    stayedToWatchPct: null,
    avgViewDurationSec: null,
    views: null,
    impressions: null,
    swipeAwayPct: null,
    curve: [],
    chartNotes: "No retention screenshot and no YouTube stats API result.",
  };
}

export function normalizeReport(raw: unknown, stats: RetentionStats): Report {
  const obj = (raw ?? {}) as Record<string, unknown>;
  const hook = (obj.hook ?? {}) as Record<string, unknown>;
  const stayed = (obj.stayedToWatch ?? {}) as Record<string, unknown>;
  const extracted = (obj.extracted ?? {}) as Record<string, unknown>;
  const rating = (value: unknown): Report["hook"]["rating"] =>
    value === "strong" || value === "ok" || value === "weak" ? value : "ok";

  const curveRaw = Array.isArray(extracted.curve) ? extracted.curve : stats.curve;
  const curve = curveRaw.map((p) => ({
    t: asNumber((p as { t?: unknown }).t, 0),
    pct: asNumber((p as { pct?: unknown }).pct, 0),
  }));

  const dips = Array.isArray(obj.dips)
    ? obj.dips.map((d) => {
        const dip = d as Record<string, unknown>;
        const t =
          typeof dip.t === "string" && dip.t.includes(":")
            ? dip.t
            : formatMmSs(asNumber(dip.t, 0));
        return {
          t,
          dropPct: asNumber(dip.dropPct, 0),
          onScreen: String(dip.onScreen ?? ""),
          cause: String(dip.cause ?? ""),
          fix: String(dip.fix ?? ""),
        };
      })
    : [];

  const rules = Array.isArray(obj.nextVideoRules)
    ? obj.nextVideoRules.map((r) => String(r)).filter(Boolean).slice(0, 5)
    : [];

  return {
    score: Math.max(0, Math.min(100, Math.round(asNumber(obj.score, 0)))),
    verdict: String(obj.verdict ?? "No verdict."),
    extracted: {
      durationSec: asNumber(extracted.durationSec, stats.durationSec),
      stayedToWatchPct: asNumber(
        extracted.stayedToWatchPct,
        stats.stayedToWatchPct ?? 0,
      ),
      avgViewDurationSec: asNumber(
        extracted.avgViewDurationSec,
        stats.avgViewDurationSec ?? 0,
      ),
      curve,
    },
    hook: {
      rating: rating(hook.rating),
      firstThreeSeconds: String(hook.firstThreeSeconds ?? ""),
      whyItWorksOrFails: String(hook.whyItWorksOrFails ?? ""),
      rewrite: String(hook.rewrite ?? ""),
    },
    dips,
    stayedToWatch: {
      rating: rating(stayed.rating),
      explanation: String(stayed.explanation ?? ""),
    },
    nextVideoRules: rules,
    distributionNote:
      typeof obj.distributionNote === "string" && obj.distributionNote.trim()
        ? obj.distributionNote
        : undefined,
  };
}

function formatMmSs(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, "0")}`;
}
