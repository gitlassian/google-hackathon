# Shorts Retention Coach

Hackathon web tool: submit a YouTube Short and a Studio retention screenshot, get a coaching report, then ask follow-up questions.

- Plan: [`docs/PLAN.md`](docs/PLAN.md)
- UI: [`frontend/`](frontend/) — Next.js, white theme, English

```bash
cd frontend
cp .env.example .env.local   # GEMINI_API_KEY
npm install && npm run dev
```

Analyze flow: screenshot (or a future YouTube stats API) → `RetentionStats` schema → Gemini watches the Short with those numbers → report + chat.
