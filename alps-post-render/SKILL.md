---
name: alps-post-render
description: >-
  Render a self-contained ALPS social-post HTML slide (4:5 feed 1080×1350, or 9:16 story
  1080×1920) to a ready-to-post 2× PNG with headless Chrome, handling the ALPS-specific render
  gotchas (wordmark as <img> not CSS-mask; Switzer @font-face; Google-Drive paths-with-spaces;
  device-scale-factor; default-background-color). Use when building or exporting ALPS Instagram /
  social carousels or single posts from HTML — to export the PNGs, re-export after an edit, or set
  up the render loop. Standalone, or callable as the RENDER step inside a larger social-post build.
  Composes with alps-design (brand correctness), alps-social-reel (9:16 motion counterpart) and
  archive-stale (version prior exports).
---

# alps-post-render

Render brand HTML slides → ready-to-post PNGs. **One job: the render step.** The *design* of the
slide (palette, type, voice, layout) is `alps-design`'s job — read it first. This skill turns the
finished HTML into pixels reliably, encoding the gotchas that cost a session to discover.

## When to use

- Exporting an ALPS Instagram/social carousel or single post built as HTML.
- Re-exporting after a copy/design tweak.
- Any "render this slide to a PNG / why is the export blank / wrong size" moment.

Standalone (`/alps-post-render`) or as the render stage another skill calls after the HTML is built.

## Preconditions

- **Google Chrome** at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` (the runner
  checks this).
- Each slide is a **self-contained HTML** at the exact pixel size (feed `1080×1350`, story
  `1080×1920`), linking a shared `posts.css` by **relative** path, with images in a relative
  `images/` and fonts in `fonts/`.

## The canonical render command

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --hide-scrollbars --force-device-scale-factor=2 --window-size=1080,1350 \
  --default-background-color=050007ff --virtual-time-budget=4000 \
  --screenshot="png/ASS2026_slide-N.png" "file://$PWD/slide-N.html"
```

`--force-device-scale-factor=2` makes the `1080×1350` window export at **2160×2700** (2×). Use
`--window-size=1080,1920` for 9:16 stories.

## Gotchas (the whole reason this skill exists)

1. **Wordmark / logo: use `<img src="logo.svg">`, NOT a CSS `mask` of the SVG.** CSS `mask` of an
   SVG renders **blank under headless Chrome**. The white SS lockup lives in the design system at
   `assets/summerschool/summerschool-logo-white.svg`.
2. **`file://` paths with spaces.** This workspace is a Google-Drive path full of spaces (and an
   `@`). Chrome handles spaces in the **top-level** `file://` URL when quoted, but a **preview
   wrapper** that loads an SVG/asset by an absolute `file://` path with spaces will **fail to load
   it** (broken-image icon). Fix: copy the asset to a space-free path (e.g. `/tmp`) before
   rendering a standalone preview, or reference assets by relative path from the slide's own folder.
3. **Fonts.** Embed Switzer via `@font-face` (woff2) and keep `--virtual-time-budget ≥ 3500` so the
   font is loaded before the screenshot fires. `font-display: block` avoids a fallback flash.
4. **`--default-background-color=RRGGBBAA`** paints the canvas behind transparent areas — use the
   Summer-School night `050007ff` so edges never flash white.
5. **Always verify the output size** (`sips -g pixelWidth -g pixelHeight OUT.png`) — a silent
   failure (missing asset, bad path) can still produce a wrong-sized or empty PNG.

## Proofing cheaply

Don't view full 2160-px PNGs to check composition — downscale first:
`sips -Z 600 png/ASS2026_slide-N.png --out /tmp/proof.png` and view the thumbnail. Good enough to
judge crop, legibility, and font-load; a fraction of the tokens.

## File conventions

- Self-contained `slide-1.html … slide-N.html` + shared `posts.css`; an `index.html` that iframes
  them all for a one-glance preview.
- Save under the social taxonomy (`60_Communications & Brand/62_Social Media/<event>/`); **archive
  prior versions to `~Archive/`, never delete** (see `archive-stale`).

## Composes with

- **`alps-design`** — read the brand system (palette, Switzer, voice, the flat-fills / no-grade /
  no-glow rules) BEFORE authoring the HTML this skill renders.
- **`alps-social-reel`** — the 9:16 **motion** (HTML→MP4) counterpart; this skill is the static-PNG
  side. Same design, two outputs.
- **`archive-stale`** — move superseded slide HTML/PNGs to `~Archive/` before re-exporting a new version.
- **`handoff`** — checkpoint a long carousel build.

## Self-verify

`bash runner.sh` renders a minimal slide and asserts the 2× PNG is exactly `2160×2700`. Run it after
changing the render command or upgrading Chrome.
