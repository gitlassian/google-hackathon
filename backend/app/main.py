import os
import shutil
import tempfile

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .routers import retention, video_qa, youtube
from .schemas import AnalyzeShortResponse
from .youtube import analyze_short_file

app = FastAPI(title="Shorts Retention Coach API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(retention.router)
app.include_router(video_qa.router)
app.include_router(youtube.router)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}


VIDEO_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
}


@app.post(
    "/analyze/file",
    response_model=AnalyzeShortResponse,
)
async def analyze_file(
    video: UploadFile = File(...),
    screenshot: UploadFile = File(...),
) -> AnalyzeShortResponse:

    if video.content_type not in VIDEO_TYPES:
        raise HTTPException(
            400,
            f"Unsupported video type {video.content_type}",
        )

    if screenshot.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            400,
            f"Unsupported screenshot type {screenshot.content_type}",
        )

    screenshot_data = await screenshot.read()

    suffix = os.path.splitext(
        video.filename or "video.mp4"
    )[1] or ".mp4"

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_video:
            temp_path = temp_video.name

            await video.seek(0)

            shutil.copyfileobj(
                video.file,
                temp_video,
            )

        report, interaction_id = analyze_short_file(
            video_path=temp_path,
            screenshot_bytes=screenshot_data,
            screenshot_mime_type=screenshot.content_type,
        )

        return AnalyzeShortResponse(
            interaction_id=interaction_id,
            report=report,
        )

    except Exception as exc:
        raise HTTPException(
            502,
            f"Gemini video analysis failed: {exc}",
        ) from exc

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
