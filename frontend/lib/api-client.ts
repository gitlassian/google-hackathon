import { GEMINI_KEY_STORAGE } from "./constants";
import type { Report, RetentionStats } from "./types";

function geminiHeaders(json = false): HeadersInit {
  const headers: Record<string, string> = {};
  if (json) headers["Content-Type"] = "application/json";
  if (typeof window !== "undefined") {
    const key = localStorage.getItem(GEMINI_KEY_STORAGE);
    if (key) headers["x-gemini-api-key"] = key;
  }
  return headers;
}

async function readError(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { error?: string };
    if (data.error) return data.error;
  } catch {
    /* ignore */
  }
  return res.statusText || "Request failed";
}

export async function analyzeShort(input: {
  youtubeUrl?: string;
  video?: File;
  screenshot?: File;
}): Promise<{ report: Report; interactionId: string; stats: RetentionStats }> {
  const form = new FormData();
  if (input.youtubeUrl) form.append("youtubeUrl", input.youtubeUrl);
  if (input.video) form.append("video", input.video);
  if (input.screenshot) form.append("screenshot", input.screenshot);

  const res = await fetch("/api/analyze", {
    method: "POST",
    headers: geminiHeaders(),
    body: form,
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json() as Promise<{
    report: Report;
    interactionId: string;
    stats: RetentionStats;
  }>;
}

export async function chatAboutShort(
  interactionId: string,
  message: string,
): Promise<{ reply: string; interactionId: string }> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: geminiHeaders(true),
    body: JSON.stringify({ interactionId, message }),
  });
  if (!res.ok) throw new Error(await readError(res));
  return res.json() as Promise<{ reply: string; interactionId: string }>;
}
