import { AnalyzeError, resolveApiKey } from "@/lib/analyze-pipeline";
import { continueChat, createClient } from "@/lib/gemini";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(request: Request) {
  try {
    const apiKey = resolveApiKey(request);
    const body = (await request.json()) as {
      interactionId?: string;
      message?: string;
    };
    const interactionId = body.interactionId?.trim();
    const message = body.message?.trim();
    if (!interactionId) {
      throw new AnalyzeError("Missing interactionId.");
    }
    if (!message) {
      throw new AnalyzeError("Type a question about this Short.");
    }

    const result = await continueChat({
      ai: createClient(apiKey),
      interactionId,
      message,
    });
    return Response.json(result);
  } catch (err) {
    const status = err instanceof AnalyzeError ? err.status : 500;
    const message = err instanceof Error ? err.message : "Chat failed.";
    return Response.json({ error: message }, { status });
  }
}
