from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import retention, youtube

app = FastAPI(title="Shorts Retention Coach API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(retention.router)
app.include_router(youtube.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
