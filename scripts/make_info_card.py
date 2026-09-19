"""Hand-author a neofetch-style info card SVG from data/profile.json.

A title bar, a user@host line, key/value rows, a highlights block, and the
neofetch color strip. Every line fades and slides in on a short stagger, so
the panel looks like it is printing next to the portrait.

    python scripts/make_info_card.py            # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py   # frozen frame, for previews
"""

import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "info-card.svg"

W, H = 700, 600
PAD = 28
BAR_H = 34
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"

BG = "#0d1117"
BAR = "#161b22"
BORDER = "#21262d"
KEY = "#39d353"
VAL = "#c9d1d9"
DIM = "#8b949e"
ACCENT = "#58a6ff"
STRIP = ["#161b22", "#f85149", "#39d353", "#d29922",
         "#58a6ff", "#bc8cff", "#39c5cf", "#c9d1d9"]

LINE_H = 30
STAGGER = 0.07
RISE = 0.45


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main():
    with open(ROOT / "data" / "profile.json", encoding="utf-8") as fh:
        p = json.load(fh)

    static = os.environ.get("STATIC") == "1"
    step = [0]

    def anim(*classes):
        """Take the next stagger slot; returns the attrs for that line.

        Classes are merged here because SVG allows only one class attribute.
        """
        i = step[0]
        step[0] += 1
        names = " ".join(classes)
        if static:
            return f'class="{names}"' if names else ""
        return (f'class="{(names + " ln").strip()}" '
                f'style="animation-delay:{i * STAGGER:.2f}s"')

    # Fit the rows to the panel instead of overflowing it: the card has to keep
    # its 700x600 box so it lines up with the portrait column in the README.
    strip_y = H - PAD - 16
    lines = 2 + len(p["rows"]) + 1 + len(p["highlights"]) + 1
    line_h = max(20.0, min(LINE_H, (strip_y - 18 - (BAR_H + PAD + 26)) / lines))

    body = []
    y = BAR_H + PAD + 6

    user_host = f"{p['user']}@{p['host']}"
    body.append(f'<text {anim("k", "big")} x="{PAD}" y="{y:.1f}">{esc(user_host)}</text>')
    y += 20
    body.append(
        f'<text {anim("dim")} x="{PAD}" y="{y:.1f}">{"-" * len(user_host)}</text>'
    )

    y += line_h + 4
    key_w = max(len(r["key"]) for r in p["rows"]) + 2
    for row in p["rows"]:
        body.append(
            f'<text {anim()} x="{PAD}" y="{y:.1f}" xml:space="preserve">'
            f'<tspan class="k">{esc(row["key"].ljust(key_w))}</tspan>'
            f'<tspan class="v">{esc(row["value"])}</tspan></text>'
        )
        y += line_h

    y += 10
    body.append(f'<text {anim("acc")} x="{PAD}" y="{y:.1f}">Highlights</text>')
    y += line_h - 4
    for item in p["highlights"]:
        body.append(
            f'<text {anim()} x="{PAD}" y="{y:.1f}" xml:space="preserve">'
            f'<tspan class="k">  * </tspan>'
            f'<tspan class="v">{esc(item)}</tspan></text>'
        )
        y += line_h - 2

    y += 6
    body.append(
        f'<text {anim("dim")} x="{PAD}" y="{y:.1f}">{esc(p["tagline"])}</text>'
    )

    # neofetch color strip, bottom-left
    sw = 26
    for i, color in enumerate(STRIP):
        body.append(
            f'<rect {anim()} x="{PAD + i * sw}" y="{strip_y}" width="{sw - 4}" '
            f'height="14" rx="2" fill="{color}"/>'
        )

    dots = "".join(
        f'<circle cx="{PAD + i * 18}" cy="{BAR_H / 2}" r="5" fill="{c}"/>'
        for i, c in enumerate(("#f85149", "#d29922", "#39d353"))
    )

    keyframes = "" if static else """
    @keyframes ln { from { opacity: 0; transform: translateY(6px); }
                    to   { opacity: 1; transform: translateY(0); } }
    .ln { opacity: 0; animation: ln %.2fs ease-out forwards; }
  """ % RISE

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="neofetch-style info card">
  <title>{esc(user_host)}</title>
  <style>
    text {{ font-family: {MONO}; font-size: 17px; fill: {VAL}; }}
    .k {{ fill: {KEY}; }}
    .v {{ fill: {VAL}; }}
    .dim {{ fill: {DIM}; }}
    .acc {{ fill: {ACCENT}; font-weight: 600; }}
    .big {{ font-size: 21px; font-weight: 700; }}
    .ttl {{ fill: {DIM}; font-size: 13px; }}{keyframes}
  </style>
  <rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{BORDER}"/>
  <path d="M0 10a10 10 0 0 1 10-10h{W - 20}a10 10 0 0 1 10 10v{BAR_H - 10}H0z" fill="{BAR}"/>
  <line x1="0" y1="{BAR_H}" x2="{W}" y2="{BAR_H}" stroke="{BORDER}"/>
  {dots}
  <text x="{W / 2}" y="{BAR_H / 2 + 4.5}" text-anchor="middle" class="ttl">neofetch</text>
{chr(10).join('  ' + b for b in body)}
</svg>
"""
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT.name}  {W}x{H}px{', static' if static else ''}")


if __name__ == "__main__":
    main()
