---
name: advance-elevenlabs-podcast
description: Generate two-host ADVANCE German podcasts (the "Gemeinsam im Gespräch" CG podcasts) with ElevenLabs from a session .docx — one female + one male voice, natural sentence pauses, Reflexionsfragen excluded, mastered to MP3. Drives translation repo scripts/podcast_tts.py with --provider elevenlabs --pause-break. Use when an agent needs to produce two-speaker podcast audio for ADVANCE (for single-speaker narration use advance-elevenlabs-narration). Composes advance-elevenlabs-voices (Lena+Christian + lessons).
---

# advance-elevenlabs-podcast

Two-host German podcast audio via ElevenLabs from a session `.docx`. Composes
[advance-elevenlabs-voices]. For single-speaker narration use
[advance-elevenlabs-narration].

## Prereqs

- Isolated translation clone (`scripts/new-agent.sh <id>`), `.venv`, `ELEVENLABS_API_KEY` in `.env`, **paid** EL plan.
- Source docs: `outputs/ADVANCE_DE_to_share/CG/Podcasts_überarbeitet/Session*.docx`
  — each holds **3 podcasts** (Speaker 1 = female, Speaker 2 = male) + Reflexionsfragen.
- Needs the COG-DE-TTS work on `main` (`--pause-break` + the form-artifact parse fix).

## Quick start — one session (3 podcasts)

Chosen voices: **Lena** (female) + **Christian** (male). 0.4s sentence pauses default.

```bash
.venv/bin/python scripts/podcast_tts.py \
  --doc ".../Podcasts_überarbeitet/Session1_Autofahren.docx" \
  --provider elevenlabs \
  --female-voice BtJhEZecBTSpKQ8EHRCJ \
  --male-voice   99yd7kp7JQfByasFNZdT \
  --pause-break 0.4 \
  --output-dir outputs/podcasts_el
```
→ `outputs/podcasts_el/<Session>/Podcast<N>/full.mp3` (+ `full.wav`, per-chunk
WAVs, `transcript.md`, `manifest.json`). The script parses 3 podcasts, **excludes
Reflexionsfragen**, renders each host turn-by-turn (EL has no native multi-speaker),
inserts pauses, concatenates, and masters (light de-ess + loudnorm to −16 LUFS).

## All sessions

`scripts/run_all_podcasts_el.sh` loops Session1–5 (15 podcasts) with the chosen
voices. **Idempotent** — cached chunks are skipped, so reruns continue after a
transient API error. ~94k chars total (~$ within an EL spend cap). Run **locally**
(EL = API calls; no server/disk needed).

## Budget pre-flight (before a big batch)

EL is **pay-per-character** — estimate + check balance before committing a run
(15 podcasts ≈ ~94k chars). In the clone:

```bash
# total chars across the source docs (uses the real parser):
.venv/bin/python - <<'PY'
import glob, sys; sys.path.insert(0,'scripts'); import podcast_tts as P
tot=0
for d in sorted(glob.glob(".../Podcasts_überarbeitet/Session*.docx")):
    _,pods=P.parse_session_docx(d)
    tot+=sum(len(P.normalize_text_for_tts(t)) for pod in pods for _,t in pod['turns'])
print(f"{tot:,} chars (+ ~8% for <break> tags)")
PY
# remaining EL balance (needs voices_read/user_read on the key; use requests, not urllib):
.venv/bin/python -c "import os,requests;from dotenv import load_dotenv;load_dotenv('.env');\
k=os.environ['ELEVENLABS_API_KEY'];s=requests.get('https://api.elevenlabs.io/v1/user/subscription',headers={'xi-api-key':k}).json();\
print('remaining:',s['character_limit']-s['character_count'],'tier:',s['tier'])"
```
If `payg` with auto-refill, runs continue past the shown limit up to the account
spend cap. The run is **idempotent** — a transient API/credit error is resumable.

## Useful flags

- `--podcast 1` — just one podcast of the doc (e.g. to let Melanie review first).
- `--stage generate` / `--stage assemble` — split API calls from local ffmpeg.
- `--pause-break 0` — disable pauses. `--no-master` — keep `full.wav` only.
- `--female-voice` / `--male-voice` — swap in any ID from
  [advance-elevenlabs-voices]/voices_de.json.

## Verify (before delivering)

- Pauses: `ffmpeg -i full.mp3 -af silencedetect=noise=-40dB:d=0.30 -f null -`
  (expect many 0.4–1.0s gaps — sentence breaks + speaker changes).
- Duration ≈ 7–8 min/podcast; loudness ~ −16/−17 LUFS.
- New source doc? Confirm `Parsed 3 podcasts` (a Word "Bottom of Form" artifact
  used to drop 2/3 — now stripped; if a future doc still mis-parses, check its
  `Podcast N` markers).
