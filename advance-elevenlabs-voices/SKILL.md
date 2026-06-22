---
name: advance-elevenlabs-voices
description: Canonical reference for ADVANCE ElevenLabs German TTS — the vetted voice registry (Christian/Lena chosen pair + Bettina/Hatti/Daniel/Marcus alternatives, with voice IDs), the EL account/model/format settings, the natural-pause method, and the hard-won post-processing lessons. Pure read-only reference; bundles voices_de.json. The shared source of truth that advance-elevenlabs-narration and advance-elevenlabs-podcast compose. Invoke whenever you need an ADVANCE German voice ID, the EL model/voice_settings, the pause convention, or to avoid the de-esser/loudnorm mistakes that pumped earlier audio.
---

# advance-elevenlabs-voices

Read-only reference for generating ADVANCE German TTS with ElevenLabs. Two task
skills compose this: [advance-elevenlabs-narration] (single-speaker) and
[advance-elevenlabs-podcast] (two-host). Mastering lives in [advance-tts-master].

## Voice registry

Machine-readable: [voices_de.json](voices_de.json) (`jq` it for IDs). All are
**standard High German** (no regional dialect). Library voices need a **PAID** EL
plan via API (free tier returns `paid_plan_required`).

| Role | Voice | ID | Character |
|---|---|---|---|
| **Podcast female (chosen)** | Lena – Warm & Professional | `BtJhEZecBTSpKQ8EHRCJ` | warm, professional |
| **COG narration + podcast male (chosen, Melanie's pick)** | Christian – Calm & Soothing | `99yd7kp7JQfByasFNZdT` | calm, soothing |
| alt female | Bettina – Warm & Einfühlsam | `Ljh056ZotKDfGTc2jGL4` | warm, empathetic |
| alt female | Hatti – Calm & Slow | `x9tGbxYQaoX72Y8bvqBh` | calm, slow (good for 60+) |
| alt male | Daniel – German Narrator | `2GbzpA60AS7Sdvj7zrZh` | classic narrator |
| alt male | Marcus – Deep & Calm German | `3mGjh1Ujzta5Mr4shzgM` | deep, calm |

## EL settings (canonical)

- **Key:** `ELEVENLABS_API_KEY` in `translation/.env` (also OneDrive master `.env`
  + server `leitneruser:~/translation/.env`). Set with `python scripts/configure_elevenlabs_key.py`.
- **Model:** `eleven_multilingual_v2` · **Format:** `pcm_24000` · **voice_settings:**
  stability 0.5 / similarity_boost 0.75 / style 0.0 / use_speaker_boost true.
- These live in `config/tts_providers.json` (`elevenlabs` block); the scripts read it.

## Natural pauses (Melanie's request: hosts should pause between sentences)

Insert ElevenLabs `<break time="0.4s" />` tags **between sentences** — rendered
inside one generation so prosody stays natural. Both scripts do this via the
`--pause-break 0.4` flag (helper `add_sentence_breaks`). **EL-only** — Gemini
can't parse the tag, so the flag is gated to `--provider elevenlabs`.

## ⚠️ Post-processing lessons (do not relearn the hard way)

- EL voices are **clean / low-sibilance** → usually need **little or no de-essing**.
- **NEVER** run the production 6-pass broadband ffmpeg `deesser` (i=0.6) on TTS —
  it crushed audio ~9 dB and **pumped** the dynamics ("aggressive compressor"
  artifact). If de-essing is truly needed, use the adaptive **split-band** de-esser
  in [advance-tts-master].
- Loudness: **two-pass LINEAR loudnorm** to **−16 LUFS** (single-pass loudnorm
  rides gain and can pump).
- **Verify before delivering:** pauses → `ffmpeg -i x.mp3 -af silencedetect=noise=-40dB:d=0.30 -f null -`;
  loudness/pumping → `ebur128` short-term (S:) spread; use `requests` not `urllib`
  for the EL REST API (urllib hits an SSL cert error here).

## Gotchas

- Free tier blocks library voices via API → use a paid plan, or fall back to a
  premade voice (e.g. Sarah `EXAVITQu4vr4xnSDxMaL`, but English-accented German).
- Query voices: `GET https://api.elevenlabs.io/v2/voices` (account) /
  `GET /v1/shared-voices?language=de` (library) — needs `voices_read` on the key.
- Scripts live in the **translation repo** (work in an isolated clone:
  `scripts/new-agent.sh`). The `--pause-break` / `--lang de` flags + the
  split-band master are on `main` (MR !8, 2026-06-17).

## Self-test

`bash runner.sh` validates [voices_de.json](voices_de.json) (valid JSON, every
voice has id+name, every `chosen` ID resolves to a listed voice). Run it after
editing the registry — the narration/podcast/master skills depend on it.
