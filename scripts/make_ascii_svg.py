"""Turn the prepped photo into a self-typing monochrome ASCII SVG.

Each row lives in its own clip rect whose width animates 0 -> full, staggered
top to bottom, with a small block cursor riding the wipe edge. Plays once and
freezes. It is SMIL inside the SVG, so GitHub animates it inside an <img>.

    python scripts/make_ascii_svg.py            # writes ascii-portrait.svg
    STATIC=1 python scripts/make_ascii_svg.py   # frozen frame, for previews
"""

import json
import os
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "ascii-portrait.svg"

FONT_SIZE = 11.0
CHAR_W = FONT_SIZE * 0.6          # monospace advance width
LINE_H = FONT_SIZE * 1.06
PAD = 16.0
ROW_STAGGER = 0.038               # seconds between rows
WIPE = 0.55                       # seconds for one row to print
MONO = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_rows(cfg):
    """Sample the prepped image onto a character grid and pick glyphs."""
    img = Image.open(ROOT / cfg["prepped"]).convert("L")
    arr = np.asarray(img, dtype=np.float32) / 255.0

    # Stretch over the lit subject only - the vignetted surround is already 0
    # and would otherwise drag the low percentile down to nothing.
    subject = arr[arr > 0.02]
    lo, hi = np.percentile(subject, 2), np.percentile(subject, 98)
    arr = np.clip((arr - lo) / max(hi - lo, 1e-6), 0, 1) ** cfg.get("gamma", 1.0)
    arr[np.asarray(img) == 0] = 0.0

    cols = int(cfg["cols"])
    rows = max(1, round(cols * (img.height / img.width) * float(cfg["char_aspect"])))
    small = Image.fromarray((arr * 255).astype(np.uint8), "L").resize(
        (cols, rows), Image.LANCZOS
    )
    lum = np.asarray(small, dtype=np.float32) / 255.0

    ramp = cfg["ramp"]
    if cfg.get("ramp_direction") == "bright-to-sparse":
        lum = 1.0 - lum
    idx = np.rint(lum * (len(ramp) - 1)).astype(int)
    return ["".join(ramp[i] for i in row).rstrip() for row in idx], cols, rows


def main():
    with open(ROOT / "config.json", encoding="utf-8") as fh:
        cfg = json.load(fh)["portrait"]

    lines, cols, rows = to_rows(cfg)
    static = os.environ.get("STATIC") == "1"

    text_w = cols * CHAR_W
    width = round(text_w + PAD * 2, 1)
    height = round(rows * LINE_H + PAD * 2, 1)

    defs, body = [], []
    for i, line in enumerate(lines):
        y = PAD + (i + 0.85) * LINE_H
        begin = round(i * ROW_STAGGER, 3)
        clip_id = f"w{i}"

        if static:
            defs.append(
                f'<clipPath id="{clip_id}"><rect x="{PAD}" y="0" '
                f'width="{text_w:.1f}" height="{height}"/></clipPath>'
            )
        else:
            defs.append(
                f'<clipPath id="{clip_id}"><rect x="{PAD}" y="0" width="0" height="{height}">'
                f'<animate attributeName="width" from="0" to="{text_w:.1f}" '
                f'dur="{WIPE}s" begin="{begin}s" fill="freeze"/></rect></clipPath>'
            )

        if line:
            body.append(
                f'<text clip-path="url(#{clip_id})" x="{PAD}" y="{y:.1f}" '
                f'xml:space="preserve">{esc(line)}</text>'
            )

        if not static:
            body.append(
                f'<rect class="cur" x="{PAD}" y="{y - LINE_H * 0.78:.1f}" '
                f'width="{CHAR_W:.2f}" height="{LINE_H * 0.82:.2f}" opacity="0">'
                f'<animate attributeName="x" from="{PAD}" to="{PAD + text_w:.1f}" '
                f'dur="{WIPE}s" begin="{begin}s" fill="freeze"/>'
                f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.02;0.92;1" '
                f'dur="{WIPE}s" begin="{begin}s" fill="freeze"/></rect>'
            )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="ASCII portrait">
  <title>ASCII portrait</title>
  <defs>{''.join(defs)}</defs>
  <style>
    text {{ font-family: {MONO}; font-size: {FONT_SIZE}px; fill: {cfg['ink']};
            letter-spacing: 0; white-space: pre; }}
    .cur {{ fill: {cfg['cursor']}; }}
  </style>
  <rect width="100%" height="100%" rx="10" fill="{cfg['background']}"/>
{chr(10).join('  ' + b for b in body)}
</svg>
"""
    OUT.write_text(svg, encoding="utf-8")
    kb = len(svg.encode()) / 1024
    print(f"wrote {OUT.name}  {cols}x{rows} chars, {width}x{height}px, {kb:.0f} KB"
          f"{', static' if static else ''}")


if __name__ == "__main__":
    main()
