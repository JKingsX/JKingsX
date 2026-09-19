"""Prep a photo for ASCII conversion.

crop -> upscale -> grayscale -> CLAHE local contrast -> blur -> vignette.

The vignette is what keeps the ASCII readable: everything outside the ellipse
falls to black, which maps to the blank end of the ramp, so only the subject
prints. rembg does this better on a real photo and is used automatically when
installed (--no-bg), but it is not required.

    python scripts/prep_photo.py                # uses config.json
    python scripts/prep_photo.py photo.jpg --no-bg --clip 2.0
"""

import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent


def remove_background(img):
    """Isolate the subject on black. No-op when rembg is not installed."""
    try:
        from rembg import remove
    except ImportError:
        return img, False
    cut = remove(img.convert("RGBA"))
    flat = Image.new("RGBA", cut.size, (0, 0, 0, 255))
    flat.paste(cut, mask=cut.split()[3])
    return flat.convert("RGB"), True


def clahe(gray, tiles=8, clip=2.0):
    """Contrast-limited adaptive histogram equalization, numpy-only.

    A clipped equalization LUT per tile, bilinearly interpolated between the
    four nearest tile centers. Same idea as cv2.createCLAHE, without dragging
    OpenCV into the toolchain.
    """
    arr = np.asarray(gray, dtype=np.uint8)
    h, w = arr.shape
    th, tw = h / tiles, w / tiles

    luts = np.empty((tiles, tiles, 256), dtype=np.float32)
    for ty in range(tiles):
        for tx in range(tiles):
            y0, y1 = int(round(ty * th)), int(round((ty + 1) * th))
            x0, x1 = int(round(tx * tw)), int(round((tx + 1) * tw))
            tile = arr[y0:y1, x0:x1]
            hist = np.bincount(tile.ravel(), minlength=256).astype(np.float32)
            limit = max(1.0, clip * tile.size / 256.0)
            excess = np.maximum(hist - limit, 0).sum()
            hist = np.minimum(hist, limit) + excess / 256.0
            cdf = np.cumsum(hist)
            luts[ty, tx] = 255.0 * (cdf - cdf[0]) / max(cdf[-1] - cdf[0], 1e-6)

    yc = (np.arange(h, dtype=np.float32) + 0.5) / th - 0.5
    xc = (np.arange(w, dtype=np.float32) + 0.5) / tw - 0.5
    y0 = np.clip(np.floor(yc), 0, tiles - 1).astype(np.int32)
    x0 = np.clip(np.floor(xc), 0, tiles - 1).astype(np.int32)
    y1 = np.clip(y0 + 1, 0, tiles - 1)
    x1 = np.clip(x0 + 1, 0, tiles - 1)
    wy = np.clip(yc - y0, 0, 1)[:, None]
    wx = np.clip(xc - x0, 0, 1)[None, :]

    ry0, ry1 = y0[:, None], y1[:, None]
    cx0, cx1 = x0[None, :], x1[None, :]
    top = luts[ry0, cx0, arr] * (1 - wx) + luts[ry0, cx1, arr] * wx
    bot = luts[ry1, cx0, arr] * (1 - wx) + luts[ry1, cx1, arr] * wx
    out = top * (1 - wy) + bot * wy
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="L")


def vignette_mask(shape, v):
    """Soft elliptical mask: 1 over the subject, 0 past the falloff."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(
        ((xx / w - v["cx"]) / v["rx"]) ** 2 + ((yy / h - v["cy"]) / v["ry"]) ** 2
    )
    return np.clip(1.0 - (d - v["start"]) / v["soft"], 0, 1).astype(np.float32)


def main():
    with open(ROOT / "config.json", encoding="utf-8") as fh:
        cfg = json.load(fh)["portrait"]

    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", default=cfg["source"])
    ap.add_argument("--out", default=cfg["prepped"])
    ap.add_argument("--no-bg", action="store_true", help="try rembg background removal")
    ap.add_argument("--no-vignette", action="store_true")
    ap.add_argument("--clip", type=float, default=cfg.get("clahe_clip", 1.6))
    ap.add_argument("--blur", type=float, default=cfg.get("blur", 2.6))
    args = ap.parse_args()

    src = ROOT / args.source
    if not src.exists():
        sys.exit(f"source photo not found: {src}")

    img = Image.open(src).convert("RGB")
    if cfg.get("crop"):
        img = img.crop(tuple(cfg["crop"]))
    up = int(cfg.get("upscale", 1))
    if up > 1:
        img = img.resize((img.width * up, img.height * up), Image.LANCZOS)

    if args.no_bg:
        img, did = remove_background(img)
        print("background removed" if did else "rembg not installed - relying on vignette")

    gray = ImageOps.grayscale(img)
    if args.clip > 0:
        gray = clahe(gray, clip=args.clip)
    if args.blur > 0:
        # Kill canvas/paint texture: at README size that texture is pure noise.
        gray = gray.filter(ImageFilter.GaussianBlur(args.blur))
    gray = ImageOps.autocontrast(gray, cutoff=3)

    arr = np.asarray(gray, dtype=np.float32) / 255.0
    if cfg.get("vignette") and not args.no_vignette:
        arr = arr * vignette_mask(arr.shape, cfg["vignette"])

    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "L").save(out)
    print(f"wrote {out.relative_to(ROOT)}  ({gray.width}x{gray.height})")


if __name__ == "__main__":
    main()
