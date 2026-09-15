# Coach — frontend

White-theme React UI for **Shorts Retention Coach**. Layout follows Bionic (document + composer) and Ollama (sidebar history). Copy is English. Gemini is not wired yet — reports are mocked.

## Run

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## What you can click

- Sidebar analyses (two sample reports)
- **+ New analysis** — empty drop zones for a Short and a Studio screenshot
- **Try a sample analysis** — staged loading, then the mock report
- Red markers / dip rows — seek the player and the retention curve
- Follow-up chips and the composer — mock chat, still in the document
- **Settings** — local Gemini API key (saved in `localStorage`, unused until the API route exists)

## Stack

Next.js App Router, React 19, Tailwind CSS v4, `lucide-react`.
