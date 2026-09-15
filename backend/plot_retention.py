"""Draw the extracted retention curve next to the original screenshot.

    .venv/bin/python plot_retention.py out/yearbook-retention.json test-images/yearbook-retention.png
    .venv/bin/python plot_retention.py test-images/yearbook-retention.png      # runs Gemini first

Writes out/<name>-check.png.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.image import imread

BG, GRID, INK, LINE, MARK = "#0f0f0f", "#3a3a3a", "#e6e6e6", "#e8479a", "#ffb1d6"


def mmss(sec: float) -> str:
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    if args[0].endswith(".json"):
        stats = json.loads(Path(args[0]).read_text())
        image = args[1] if len(args) > 1 else None
        name = Path(args[0]).stem
    else:
        from app.extractor import extract_retention_stats_from_file

        stats = extract_retention_stats_from_file(args[0]).model_dump()
        image = args[0]
        name = Path(args[0]).stem

    curve = stats["retention_curve"]
    xs = [p["t"] for p in curve]
    ys = [p["pct"] for p in curve]
    dur = stats.get("video_duration_sec") or (xs[-1] if xs else 0)
    ymax = max(150, int((max(ys) + 25) // 50 * 50)) if ys else 150

    fig = plt.figure(figsize=(16, 7), facecolor=BG)
    if image:
        ax_img = fig.add_axes([0.02, 0.05, 0.42, 0.9])
        ax_img.imshow(imread(image))
        ax_img.set_axis_off()
        ax_img.set_title("Original screenshot", color=INK, fontsize=12, loc="left")
        ax = fig.add_axes([0.5, 0.15, 0.46, 0.72])
    else:
        ax = fig.add_axes([0.08, 0.15, 0.88, 0.72])

    ax.set_facecolor(BG)
    ax.step(xs, ys, where="post", color=LINE, linewidth=2)
    for d in stats.get("biggest_drops", [])[:3]:
        ax.plot([d["from_sec"], d["to_sec"]], [d["from_pct"], d["to_pct"]], "o", color=MARK, ms=6)
        ax.annotate(
            f"-{d['drop_pct_points']:.0f} pts\n{mmss(d['from_sec'])}→{mmss(d['to_sec'])}",
            xy=(d["to_sec"], d["to_pct"]), xytext=(6, -28), textcoords="offset points",
            color=INK, fontsize=9,
        )

    ax.set_xlim(0, dur)
    ax.set_ylim(0, ymax)
    ax.set_yticks(range(0, ymax + 1, 50))
    ax.set_yticklabels([f"{v}%" for v in range(0, ymax + 1, 50)], color=INK)
    ax.set_xticks([0, dur / 2, dur])
    ax.set_xticklabels([mmss(0), mmss(dur / 2), mmss(dur)], color=INK)
    ax.grid(axis="y", color=GRID, linewidth=1)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)

    stw = stats.get("stayed_to_watch_pct")
    avd = stats.get("avg_view_duration_sec")
    ax.set_title(
        f"Extracted by Gemini  ·  stayed to watch {stw}%  ·  avg view {mmss(avd) if avd else '—'}\n"
        f"duration {mmss(dur)}  ·  {len(curve)} points  ·  confidence {stats.get('reading_confidence')}",
        color=INK, fontsize=11, loc="left",
    )

    out = Path("out") / f"{name}-check.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, dpi=110, facecolor=BG)
    print(out)


if __name__ == "__main__":
    main()
