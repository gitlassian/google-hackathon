from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .extractor import extract_retention_stats
from .schemas import RetentionStats

app = FastAPI(title="Shorts Retention Coach API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract-retention", response_model=RetentionStats)
async def extract_retention(screenshot: UploadFile = File(...)) -> RetentionStats:
    """Upload a YouTube Studio screenshot; get stayed-to-watch and retention curve data."""
    if screenshot.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type {screenshot.content_type}; use PNG, JPEG or WebP")
    data = await screenshot.read()
    if len(data) > 15 * 1024 * 1024:
        raise HTTPException(413, "Screenshot larger than 15 MB")
    try:
        return extract_retention_stats(data, screenshot.content_type)
    except Exception as exc:  # surface Gemini errors to the client during the hackathon
        raise HTTPException(502, f"Gemini extraction failed: {exc}") from exc
