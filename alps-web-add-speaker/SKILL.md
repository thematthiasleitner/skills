---
name: alps-web-add-speaker
description: Add or refresh a speaker / facilitator / team member on an ALPS Foundation website — process their photo to a portrait JPEG and add their bio entry, then ship it. Use when adding speakers/people to an ALPS site (e.g. summerschool.alps.foundation) or updating a photo or bio. Crops photos to a minimum 4:5 ratio so faces stay fully visible (Pillow), drops them in the assets folder with a slug, and adds an entry following the site's conventions (alphabetical by last name, short ≤100-word bio with <strong>/<mark> highlights, affiliation badges, optional scholar link). Discovers the source folder and target component; asks when ambiguous. Composes with alps-web-ship to build + deploy.
---

# Add / refresh a speaker on an ALPS website

Composable on top of **alps-web-ship**. Discover inputs; never hardcode Drive or repo paths; ask when ambiguous.

## 1. Gather inputs (discover, then confirm)

- **Source photos + bios** usually live in a Google Drive shared-drive folder (e.g. a "Speakers" / "Animators" folder). Search for it — don't assume a path:
  `find ~/Library/CloudStorage -maxdepth 7 -type d -iname '*speaker*' 2>/dev/null`
  If zero or several plausible matches → **AskUserQuestion** with the candidates.
- **Target repo + component.** Locate the data array that holds people: in the repo, `grep -rln "id: 'speaker-\|affiliations:\|speakers\b" src/components`. Inspect existing entries to learn the exact field shape, slug scheme, and asset path (`public/assets/...`). If multiple components/sites are plausible → ask.

## 2. Process the photo

Inspect a couple of existing assets first to match dimensions/naming. Then:

`python3 scripts/crop_speaker_photo.py <src.png> <repo>/public/assets/speakers-<slug>.jpg [--fx 0.42]`

- Target is **minimum 4:5** (faces fully visible) — the agreed ALPS ratio. Portraits taller than 4:5 are kept as-is; wider/landscape/square photos get a width crop.
- `--fx` is the face's horizontal position (0–1). For landscape or off-centre photos, **open the source first**, estimate where the face is, and pass `--fx`. Default 0.5.
- **Always VIEW the output** (Read the produced .jpg) to confirm the whole face is in frame. Re-run with a different `--fx` if a face is clipped.

## 3. Add the entry (match the site's conventions)

Mirror the existing entries exactly. Typical fields: `id` (`speaker-<slug>`), `name`, optional `title`, `affiliations` (short badge text), optional `scholar`, `image`, `bio` (array of HTML paragraphs).

- **Order:** insert alphabetically by **last name** if the existing list is ordered that way (check first).
- **Bio:** trim to **≤ ~100 words**, keep house style — `<strong>` for institutions, `<mark>` for key topics.
- **Linking:** if the site auto-links the schedule to bios by speaker **name**, the `name` must match the schedule string exactly (incl. accents) or the link won't resolve.

## 4. Verify & ship

- View the cropped photo (step 2) and re-read the new entry for word count / highlights.
- Hand off to **alps-web-ship**: build (must exit 0), grep the built HTML for the new slug/name, PR → merge → poll live for the new `speakers-<slug>.jpg` returning 200.

## Ambiguity → ask

Source folder not found or multiple matches; unclear slug/naming scheme; which component/site; odd photo where the face crop is uncertain; whether a person belongs in the schedule too. Confirm via AskUserQuestion rather than guessing.
