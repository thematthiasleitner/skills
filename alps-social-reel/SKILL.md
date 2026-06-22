---
name: alps-social-reel
description: Turn an APPROVED ALPS HTML slide/carousel deliverable into a polished, on-brand 9:16 Instagram reel (1080×1920, silent — audio is added later in Instagram) using HyperFrames (HTML→MP4). Use when asked to make/create a reel or short video from existing ALPS posts/slides/a carousel, "turn this carousel into a reel", or any 9:16 motion version of approved social content. Re-cuts the approved design into motion — it does NOT invent a new design. Composes the installed hyperframes skill family + the ALPS brand system.
---

# ALPS social reel from approved slides

Re-cut an **already-approved** ALPS HTML deliverable (e.g. a feed carousel) into a moving 9:16 reel.
The design is already signed off — your job is motion + format, **not** a redesign. Stay faithful to
the approved look; ALPS brand restraint **overrides** HyperFrames' generic "8–10 elements per scene"
density advice (no glows, grades, decorative gradients — see the org brand rules).

**Preconditions:** the `hyperframes` skill family installed (it is, globally in `~/.claude/skills/`),
Node 22+, ffmpeg. Known render traps live in [[hyperframes-gotchas]] — read it before authoring.

## 1. Read the source of truth (don't redesign)

- Find the approved deliverable in `60_Communications & Brand/62_Social Media/…`. Read its **CSS**
  (brand tokens, scrims), the **slide HTML** (exact copy), and the **captions.md / HANDOFF.md**
  (final copy, pricing, alt text, standing caveats like "confirm waiting-list status before posting").
- **View the rendered PNGs**, not just the markup — match the actual pixels.
- Reuse the exact hex values, the local Switzer `@font-face`, and the copy verbatim. Don't re-derive.

## 2. Format + Instagram safe zones

- **1080×1920, silent.** Audio is added in Instagram — render no audio track (verify with ffprobe).
- Keep critical text in the **top ~75%**: IG overlays the caption/audio at the bottom (~250 px) and an
  action rail on the right (~120 px). Text blocks left-aligned with a `max-width` clear the rail.
- ~20–22 s is a good length; cover + bridge hold ~2.8 s, testimonials ~2.5–3 s, a text-dense close
  holds ~3 s+ for reading.

## 3. Isolated, self-contained project (taxonomy + archive rules)

- Build in a `reel/` subfolder **inside the same approved-deliverable folder** (org rule: save in the
  right place; archive, never overwrite, prior versions).
- Copy assets in so it re-renders anywhere; **downscale photos** to ~1920 px long edge:
  `sips --resampleHeightWidthMax 1920 src.jpg --out reel/images/src.jpg` (originals are often
  ~2880×3840 — wasteful on a synced Drive). Copy the `.woff2` and logo SVG too.

## 4. Author the composition (HyperFrames)

Single `index.html`, root `data-composition-id`/`data-width="1080"`/`data-height="1920"`. Pattern that
works for slide→reel:

- **Stacked scenes:** each scene a full-screen `.scene` div; scene 1 visible, scenes 2+ `opacity:0`,
  z-index increasing. A crossfade = fade the next (opaque, full-bleed) scene in over the previous
  (`tl.to("#sN",{opacity:1,...})`). The transition IS the exit — never exit-animate inner content.
- **Ken Burns:** animate each photo's `scale` with `ease:"none"`, keeping **scale ≥ 1** so edges stay
  covered; `.photo{overflow:hidden}` clips it. Vary zoom-in/zoom-out per scene.
- **Entrances:** every scene's elements animate IN (`gsap.from`), 3+ eases, staggered. Restrained.
- Reuse the brand CSS (canvas, scrims, type scale, the iridescent pill, etc.) adapted to the taller frame.
- Avoid the three [[hyperframes-gotchas]]: name the font literally (not `var(--font)`); mark `.scene`
  `data-layout-allow-overlap` + Ken-Burns imgs `data-layout-allow-overflow`; use **literal** GSAP
  selectors (no template literals).

## 5. Lint → inspect → render → verify with real pixels

```
cd reel
npx hyperframes lint            # 0 errors (font/timeline)
npx hyperframes inspect         # cross-scene overlap warnings are EXPECTED (see gotchas)
npx hyperframes render --quality draft --output /tmp/draft.mp4
# QA on actual frames — extract one per scene at its hold and VIEW them:
ffmpeg -loglevel error -ss <t> -i /tmp/draft.mp4 -frames:v 1 -vf scale=540:-1 /tmp/f.png -y
npx hyperframes render --quality high --fps 30 --output ASS2026_..._reel.mp4
ffprobe …  # confirm 1080x1920, fps, and 0 audio streams
```

Always eyeball extracted frames — `inspect` is geometry-only and can't judge legibility or the look.
For silkier slow motion offer `--fps 60`.

## 6. Deliver

- Final MP4 + a short `reel/README.md` (specs, structure, re-render command) in the `reel/` folder.
- Update the deliverable's project-location memory to point at the reel.
- Report the path; offer tweaks (pacing/length, 60 fps, beat-synced cut if they pick a track, leaner close).

## Composes with

- **`hyperframes`** — composition contract, transitions, motion (authoring rules).
- **`hyperframes-cli`** — `lint` / `inspect` / `render` dev loop.
- **`alps-design`** (or the brand-system folder if the skill isn't loaded) — brand tokens/voice.
- **[[hyperframes-gotchas]]** — the lint/inspect traps to avoid.
- Org taxonomy + archive rules for where the deliverable lands.
