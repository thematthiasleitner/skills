---
name: advance-tts-master
description: Master raw ADVANCE TTS clips (ElevenLabs or Gemini) into a clean, loudness-matched deliverable WITHOUT the pumping/"aggressive-compressor" artifact that ruined earlier audio. Encodes the correct chain — per-clip normalize, optional soft ADAPTIVE split-band de-esser, two-pass LINEAR loudnorm to −16 LUFS — and the anti-patterns to avoid (6-pass broadband ffmpeg deesser; single-pass dynamic loudnorm). Drives translation repo scripts/tts_sample_postprocess.py. Use when an agent has raw TTS WAV clips to assemble/master, or is choosing de-ess/loudness settings, or is debugging a "voices pump / sound over-compressed" complaint. Composed by advance-elevenlabs-narration; see advance-elevenlabs-voices.
---

# advance-tts-master

Turn raw TTS clips into a clean, −16 LUFS deliverable. The mastering half of the
ADVANCE TTS pipeline. Reference: [advance-elevenlabs-voices].

## The chain (what `scripts/tts_sample_postprocess.py` does)

1. **Per-clip normalize** to −18 dBFS avg, −1 dB peak ceiling.
2. **Soft ADAPTIVE split-band de-esser** (on by default; tames sharp "s"):
   `acrossover` split at 6 kHz → gentle `acompressor` (ratio 4:1) on the **high
   band only**, threshold = the clip's *measured* >6 kHz peak − headroom (default
   20 dB), recombined flat. Touches only loud sibilant transients; voice body +
   level stay intact.
3. **Light noise gate** (agate) to trim inter-phrase breath.
4. **Two-pass LINEAR loudnorm** to −16 LUFS / −1.5 dBTP (measure → single linear
   gain + true-peak limit — no gain-riding, so it cannot pump).

```bash
.venv/bin/python scripts/tts_sample_postprocess.py \
  --clips outputs/<name>/session_1 --out outputs/<name>/full.mp3
# stronger "s" taming: --deess-headroom 16  (lower = stronger)
# clean EL voice, skip de-ess entirely:   --no-deess
# skip breath gate:                        --no-gate
```
(`podcast_tts.py` has its own built-in light master — `deesser i=0.12` + loudnorm
— so podcasts don't need this step; use it for narration / loose clips.)

## ⚠️ Anti-patterns (these caused real, shipped-then-recalled bad audio)

- **NEVER the 6-pass broadband ffmpeg `deesser` (i=0.6, m=0.7).** It dropped a
  Gemini/Kore clip **~9 dB** and **pumped** the dynamics; a following loudnorm then
  makeup-gained the pump to full volume = "aggressive compressor". Even *one*
  gentle broadband pass costs ~4 dB. Use the split-band de-esser above instead.
- **NEVER single-pass `loudnorm=I=-16:...`** — it runs in dynamic mode and rides
  the gain (pumps). Always two-pass `linear=true` with measured values.
- ElevenLabs voices are already clean (>6 kHz peak often ≪ Gemini's) → frequently
  need **no de-essing at all** (`--no-deess`).

## Diagnose / verify

- **Pumping** ("sounds over-compressed"): `ffmpeg -i x.mp3 -af ebur128 -f null -`
  and look at short-term `S:` values — a clean clip's voiced spread is ~7–9 LU; a
  pumped one balloons to ~11+ with a low-freq wobble. Compare stages to localize
  which step introduced it.
- **Sibilance**: `ffmpeg -i x.wav -af "highpass=f=6000,astats=metadata=1:reset=0" -f null -`
  → compare >6 kHz Peak vs RMS (sharp "s" = peaks near 0 dB over a ~−25 dB average).
- **Pauses**: `ffmpeg -i x.mp3 -af silencedetect=noise=-40dB:d=0.30 -f null -`.
- **Loudness**: integrated should land ~ −16 LUFS, true peak < −1 dBTP.
