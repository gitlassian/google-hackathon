import { AnalyzeError, resolveApiKey, runAnalysis } from "@/lib/analyze-pipeline";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(request: Request) {
  try {
    const apiKey = resolveApiKey(request);
    const form = await request.formData();
    const youtubeUrl = String(form.get("youtubeUrl") ?? "");
    const video = asFile(form.get("video"));
    const screenshot = asFile(form.get("screenshot"));

    const result = await runAnalysis({
      apiKey,
      youtubeUrl,
      video,
      screenshot,
    });

    return Response.json(result);
  } catch (err) {
    const status = err instanceof AnalyzeError ? err.status : 500;
    const message = err instanceof Error ? err.message : "Analyze failed.";
    return Response.json({ error: message }, { status });
  }
}

function asFile(value: FormDataEntryValue | null): File | null {
  if (value instanceof File && value.size > 0) return value;
  return null;
}
