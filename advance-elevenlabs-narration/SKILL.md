---
name: advance-elevenlabs-narration
description: Generate single-speaker ADVANCE German narration audio (e.g. COG course manual) with ElevenLabs, using the project's vetted voice + natural sentence pauses + correct mastering. Drives translation repo scripts/tts_generate.py with --provider elevenlabs --lang de --pause-break. Use when an agent needs to voice German narration / a manual / a script for ADVANCE via ElevenLabs (not a two-host podcast — for that use advance-elevenlabs-podcast). Composes advance-elevenlabs-voices (voice IDs + lessons) and advance-tts-master (loudness/de-ess).
---

# advance-elevenlabs-narration

Single-speaker German narration via ElevenLabs. Composes
[advance-elevenlabs-voices] (voices, settings, pause method, lessons) and
[advance-tts-master] (mastering). For two-host podcasts use
[advance-elevenlabs-podcast].

## Prereqs

- Work in an **isolated translation clone** (`scripts/new-agent.sh <id>`), `.venv` active.
- `ELEVENLABS_API_KEY` in `.env`; **paid** EL plan (free tier blocks library voices).
- Needs the COG-DE-TTS work on `main` (`--lang de` / `--pause-break`).

## Quick start

1. **Structured script JSON** the generator consumes:
   ```json
   {"sessions":[{"number":1,"title":"...","segments":[
     {"type":"text","content":"Vielen Dank, dass Sie ...","id":"p1"},
     {"type":"section","title":"break"},
     {"type":"text","content":"Zunächst ...","id":"p2"}]}]}
   ```
   (For the COG manual, the yellow-highlighted passages are the script — see the
   `project_cog_german_tts` memory + `build_cog_de_sample.py`.)

2. **Pick the voice** (default narration = Christian) — set it for the session in a
   provider config; copy the canonical one and edit `elevenlabs.voices.COG.<n>`:
   ```json
   { "elevenlabs": { "model_id":"eleven_multilingual_v2", "output_format":"pcm_24000",
     "voice_settings":{"stability":0.5,"similarity_boost":0.75,"style":0.0,"use_speaker_boost":true},
     "voices": { "COG": { "1": "99yd7kp7JQfByasFNZdT" } } } }
   ```

3. **Generate** (Christian, German, 0.4s sentence pauses):
   ```bash
   .venv/bin/python scripts/tts_generate.py \
     --script script.json --programme COG --provider elevenlabs --lang de \
     --pause-break 0.4 --provider-config my_providers.json \
     --output-dir outputs/<name>
   ```
   → per-chunk WAVs in `outputs/<name>/session_1/`.

4. **Master** → one `-16 LUFS` MP3, per [advance-tts-master]:
   ```bash
   .venv/bin/python scripts/tts_sample_postprocess.py \
     --clips outputs/<name>/session_1 --out outputs/<name>/full.mp3
   ```

## Verify (always, before delivering)

- Pauses present: `ffmpeg -i full.mp3 -af silencedetect=noise=-40dB:d=0.30 -f null -`
- Loudness ~ −16 LUFS, no pump: `ffmpeg -i full.mp3 -af ebur128 -f null -` (check
  short-term `S:` spread is steady, not swinging).
- Clip duration ≈ chars ÷ ~16/s → catches truncation.

## Notes

- `--pause-break` is EL-only (gated); Gemini ignores it.
- Other voices / the "calm & slow" option (Hatti) etc.: see
  [advance-elevenlabs-voices]/voices_de.json.
