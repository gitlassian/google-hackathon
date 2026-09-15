import type { RetentionStats } from "./types";

/**
 * Teammate hook.
 *
 * When the video/stats API exists, set YOUTUBE_STATS_API_URL to an endpoint
 * that accepts `{ youtubeUrl: string }` and returns RetentionStats JSON
 * (`source` should be `"youtube_api"`).
 *
 * Returning null means "I don't have numbers" — the pipeline then reads
 * the Studio screenshot with Gemini.
 */
export async function fetchYoutubeStats(
  youtubeUrl: string,
): Promise<RetentionStats | null> {
  const endpoint = process.env.YOUTUBE_STATS_API_URL;
  if (!endpoint) return null;

  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ youtubeUrl }),
  });
  if (!res.ok) return null;
  const data = (await res.json()) as RetentionStats;
  if (!data || !Array.isArray(data.curve)) return null;
  return { ...data, source: "youtube_api" };
}
