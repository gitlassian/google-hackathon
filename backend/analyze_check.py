from pathlib import Path

from app.gemini_video import analyze_short


YOUTUBE_URL = "https://www.youtube.com/shorts/zq4yvyfk4Eo"

screenshot = Path("test-images/redbull-retention.png").read_bytes()

report, interaction_id = analyze_short(
    youtube_url=YOUTUBE_URL,
    screenshot_bytes=screenshot,
    screenshot_mime_type="image/png",
)

print("\n=== REPORT ===")
print(report.model_dump_json(indent=2, by_alias=True))

print("\n=== INTERACTION ID ===")
print(interaction_id)