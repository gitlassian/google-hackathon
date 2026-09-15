# Coach — frontend

White-theme React UI for **Shorts Retention Coach**. Layout follows Bionic / Ollama. Copy is English.

## Run

```bash
cd frontend
cp .env.example .env.local   # then paste GEMINI_API_KEY
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) (or 3001 if 3000 is taken).

## Analyze pipeline

1. Browser `POST /api/analyze` with a YouTube URL and/or video file, plus an optional Studio screenshot.
2. Stats, in order:
   - `YOUTUBE_STATS_API_URL` if set (`lib/youtube-stats.ts` — teammate hook)
   - else Gemini reads the screenshot into `RETENTION_STATS_SCHEMA` (`lib/schema.ts`)
3. Gemini watches the Short (static 1 fps) with those numbers in the prompt and returns the coaching report.
4. Follow-up chat: `POST /api/chat` with `previous_interaction_id` so the video stays in context.

**Try a sample analysis** still plays a mock report (no API key needed).

## Stack

Next.js App Router, React 19, Tailwind CSS v4, `@google/genai`, `lucide-react`.
