from pathlib import Path

from app.youtube import analyze_short_file


video_path = "test-images/my-video.mp4"

screenshot = Path(
    "test-images/retention.png"
).read_bytes()

report, interaction_id = analyze_short_file(
    video_path=video_path,
    screenshot_bytes=screenshot,
    screenshot_mime_type="image/png",
)

print("\n=== REPORT ===")
print(
    report.model_dump_json(
        indent=2,
        by_alias=True,
    )
)

print("\n=== INTERACTION ID ===")
print(interaction_id)
