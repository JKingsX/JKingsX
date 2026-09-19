# How this profile is built

Three animated SVGs, generated locally by Python, committed to the repo, and
placed by `README.md`. No third-party stats services, no token, no JavaScript —
GitHub strips `<script>` and inline `style` from READMEs but does render SVG
and runs its SMIL / CSS-keyframe animations.

```
ascii-portrait.svg   self-typing monochrome ASCII portrait   390px
info-card.svg        neofetch-style panel                    470px
contrib-heatmap.svg  real contribution calendar              860px  (= 390 + 470)
```

## Install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r scripts/requirements.txt
```

## Regenerate

| When | Command |
| --- | --- |
| New photo | `python scripts/prep_photo.py` then `python scripts/make_ascii_svg.py` |
| Card content changed (`data/profile.json`) | `python scripts/make_info_card.py` |
| Contributions (also runs daily in CI) | `python scripts/fetch_contributions.py` then `python scripts/render_heatmap_svg.py` |

`STATIC=1` on any of the three generators emits a frozen frame instead of the
animation — useful for previewing, never commit those.

## Tuning the portrait

Everything lives under `portrait` in `config.json`:

- **`crop`** — `[left, top, right, bottom]` on the source photo. A tight crop on
  the subject is the single biggest quality win; a full scene turns to mush.
- **`vignette`** — soft ellipse (normalized coords). Outside it, pixels fall to
  black, which maps to the blank end of the ramp, so only the subject prints.
  This stands in for background removal. Install `rembg` and run
  `python scripts/prep_photo.py --no-bg` for the real thing.
- **`ramp`** — glyphs ordered dark→bright. The default is *measured*, not
  guessed: each character's ink coverage was rendered and sampled, then glyphs
  were picked at even coverage steps. Consolas tops out at ~31% coverage on
  `@`, which is why the ink color is near-white — otherwise the whole portrait
  reads dim.
- **`gamma`** — below 1 lifts the midtones, above 1 deepens them.
- **`cols`** — character grid width. More columns means finer detail and a
  bigger SVG; 110 lands around 46 KB.

## Daily refresh

`.github/workflows/update-profile-art.yml` re-scrapes and re-renders the
heatmap at 06:17 UTC, then commits with `[skip ci]` so the bot's own push does
not re-trigger the run. It needs `contents: write`, which is already declared.
Trigger it once by hand from the **Actions** tab to confirm it commits.

## GitHub markdown gotchas

- Inline `style` is stripped. The only vertical spacing that survives is `<br>`.
- `<h1>` and `<h2>` draw a full-width underline rule — use `<h3>` for titles.
- Side-by-side images need a `<table>`; nothing else is reliable.
- Keep the widths aligned: heatmap `860` = portrait `390` + card `470`.

Based on [Avi Vashishta's write-up](https://www.avivashishta.com/blog/build-animated-github-profile-readme).

## When a change does not show up on the profile

The `?v=N` query on each image in `README.md` exists only to break caches —
browsers and GitHub's image layer will happily serve an old SVG for hours
after a push. Bump the number when you change the art and the old frame is
stuck. The URL changes, so nothing cached matches.

To check what GitHub is actually serving, bypass the page entirely:

```
curl -sL https://github.com/USERNAME/USERNAME/raw/main/info-card.svg | head
```
