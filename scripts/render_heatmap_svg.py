"""Render data/contributions.json as an animated contribution heatmap SVG.

53 weeks of rounded boxes that reveal on a diagonal sweep (CSS keyframes that
play once on load and freeze - no looping glow), plus month labels, a
Less->More legend and a stats footer.

    python scripts/render_heatmap_svg.py            # writes contrib-heatmap.svg
    STATIC=1 python scripts/render_heatmap_svg.py   # frozen frame, for previews
"""

import datetime as dt
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "contrib-heatmap.svg"

CELL, GAP = 12, 3
PITCH = CELL + GAP
PAD = 26
GUTTER = 34            # room for the Mon/Wed/Fri labels
MONTH_H = 20
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DIAG = 0.022           # seconds added per step along the diagonal
POP = 0.42             # seconds for one cell to land


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_weeks(days):
    """Bucket days into columns, starting each column on Sunday like GitHub."""
    weeks, current = [], [None] * 7
    for day in days:
        wd = (dt.date.fromisoformat(day["date"]).weekday() + 1) % 7  # Sun=0
        if wd == 0 and any(c is not None for c in current):
            weeks.append(current)
            current = [None] * 7
        current[wd] = day
    if any(c is not None for c in current):
        weeks.append(current)
    return weeks


def main():
    cfg = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))["heatmap"]
    data = json.loads((ROOT / "data" / "contributions.json").read_text(encoding="utf-8"))
    static = os.environ.get("STATIC") == "1"

    palette = cfg["palette"]
    weeks = to_weeks(data["days"])
    grid_x = PAD + GUTTER
    grid_y = PAD + MONTH_H

    width = grid_x + len(weeks) * PITCH - GAP + PAD
    footer_y = grid_y + 7 * PITCH + 26
    height = footer_y + 52

    cells, months, seen = [], [], {}
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            if day is None:
                continue
            x = grid_x + wi * PITCH
            y = grid_y + di * PITCH
            level = min(day["level"], len(palette) - 1)
            # Levels are GitHub's 0-4; keep the neon top end for the best days.
            if day["count"] and day["count"] >= data["stats"]["best_day"]["count"] * 0.8:
                level = len(palette) - 1
            delay = "" if static else f' style="animation-delay:{(wi + di) * DIAG:.3f}s"'
            title = (f'{day["count"]} contribution{"" if day["count"] == 1 else "s"} '
                     f'on {day["date"]}')
            cells.append(
                f'<rect class="d" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                f'fill="{palette[level]}"{delay}><title>{esc(title)}</title></rect>'
            )

        # Label a column whenever its first day rolls into a new month, so the
        # partial first week still gets its name.
        first = next((d for d in week if d), None)
        if first:
            month = dt.date.fromisoformat(first["date"]).month
            if month != seen.get("last"):
                seen["last"] = month
                months.append(
                    f'<text class="lbl" x="{grid_x + wi * PITCH}" y="{PAD + 12}">'
                    f"{MONTHS[month - 1]}</text>"
                )

    day_labels = [
        f'<text class="lbl" x="{PAD}" y="{grid_y + di * PITCH + CELL - 2}">{name}</text>'
        for di, name in DAY_LABELS.items()
    ]

    # legend, bottom right
    legend_x = width - PAD - (len(palette) * PITCH + 76)
    legend = [f'<text class="lbl" x="{legend_x}" y="{footer_y + 10}">Less</text>']
    for i, color in enumerate(palette):
        legend.append(
            f'<rect class="lg" x="{legend_x + 36 + i * PITCH}" y="{footer_y}" '
            f'width="{CELL}" height="{CELL}" rx="2.5" fill="{color}"/>'
        )
    legend.append(
        f'<text class="lbl" x="{legend_x + 42 + len(palette) * PITCH}" '
        f'y="{footer_y + 10}">More</text>'
    )

    s = data["stats"]
    headline = f'{data["total"]:,} contributions in the last year'
    detail = (f'current streak {s["current_streak"]}d   ·   '
              f'longest {s["longest_streak"]}d   ·   '
              f'best day {s["best_day"]["count"]} on {s["best_day"]["date"]}   ·   '
              f'{s["active_days"]} active days')

    keyframes = "" if static else """
    @keyframes pop { from { opacity: 0; transform: translateY(-7px) scale(.72); }
                     to   { opacity: 1; transform: translateY(0) scale(1); } }
    .d { opacity: 0; transform-box: fill-box; transform-origin: center;
         animation: pop %.2fs cubic-bezier(.2,.9,.3,1.2) forwards; }
  """ % POP

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(headline)}">
  <title>{esc(headline)}</title>
  <style>
    text {{ font-family: {MONO}; fill: {cfg['text']}; }}
    .lbl {{ font-size: 11px; }}
    .hd {{ font-size: 15px; fill: {cfg['accent']}; font-weight: 600; }}
    .sub {{ font-size: 11.5px; }}{keyframes}
  </style>
  <rect width="{width}" height="{height}" rx="10" fill="{cfg['background']}"/>
{chr(10).join('  ' + m for m in months)}
{chr(10).join('  ' + d for d in day_labels)}
{chr(10).join('  ' + c for c in cells)}
{chr(10).join('  ' + l for l in legend)}
  <text class="hd" x="{PAD}" y="{footer_y + 10}">{esc(headline)}</text>
  <text class="sub" x="{PAD}" y="{footer_y + 32}">{esc(detail)}</text>
</svg>
"""
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.name}  {len(weeks)} weeks, {width}x{height}px"
          f"{', static' if static else ''}")


if __name__ == "__main__":
    main()
