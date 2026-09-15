import { isYouTubeUrl } from "./format";
import {
  analyzeVideo,
  createClient,
  emptyStats,
  extractStatsFromScreenshot,
  uploadMedia,
} from "./gemini";
import type { Report, RetentionStats } from "./types";
import { fetchYoutubeStats } from "./youtube-stats";

export class AnalyzeError extends Error {
  status: number;
  constructor(message: string, status = 400) {
    super(message);
    this.status = status;
  }
}

export async function runAnalysis(options: {
  apiKey: string;
  youtubeUrl: string;
  video: File | null;
  screenshot: File | null;
}): Promise<{ report: Report; interactionId: string; stats: RetentionStats }> {
  const youtubeUrl = options.youtubeUrl.trim();
  if (youtubeUrl && !isYouTubeUrl(youtubeUrl)) {
    throw new AnalyzeError(
      "Link must be a youtube.com/shorts, youtube.com/watch, or youtu.be URL.",
    );
  }
  if (!youtubeUrl && !options.video) {
    throw new AnalyzeError(
      "Paste a public Shorts URL or upload the video file.",
    );
  }

  const ai = createClient(options.apiKey);

  let stats: RetentionStats | null = null;
  if (youtubeUrl) {
    stats = await fetchYoutubeStats(youtubeUrl);
  }
  if (!stats && options.screenshot) {
    stats = await extractStatsFromScreenshot(ai, options.screenshot);
  }
  if (!stats) {
    stats = emptyStats();
  }

  const video = options.video
    ? await (async () => {
        const uploaded = await uploadMedia(ai, options.video as File, "video/mp4");
        return {
          kind: "file" as const,
          uri: uploaded.uri,
          mimeType: uploaded.mimeType,
        };
      })()
    : { kind: "youtube" as const, url: youtubeUrl };

  const { report, interactionId } = await analyzeVideo({
    ai,
    video,
    stats,
    screenshot: options.screenshot ?? undefined,
  });

  return { report, interactionId, stats };
}

export function resolveApiKey(request: Request): string {
  const header = request.headers.get("x-gemini-api-key")?.trim();
  if (header) return header;
  const env = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (env?.trim()) return env.trim();
  throw new AnalyzeError(
    "Missing Gemini API key. Add GEMINI_API_KEY to frontend/.env.local or paste it in Settings.",
    401,
  );
}
