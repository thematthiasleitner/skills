#!/usr/bin/env bash
# Self-test for advance-elevenlabs-voices: validate the bundled voice registry.
# The narration / podcast / master skills all depend on voices_de.json, so a
# malformed registry (bad JSON, missing id, a `chosen` ID that isn't in the
# lists) would silently break generation. Deterministic, no network. Exit != 0
# on any failure so it wires into Layer-C-style CI.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
python3 - "$DIR/voices_de.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))

errs = []
# required top-level settings
for k in ("model_id", "output_format", "voice_settings", "voices", "chosen"):
    if k not in d:
        errs.append(f"missing top-level key: {k}")

voices = d.get("voices", {})
ids = {}
for gender in ("female", "male"):
    lst = voices.get(gender)
    if not lst:
        errs.append(f"voices.{gender} is empty/missing")
        continue
    for v in lst:
        if not v.get("id"):
            errs.append(f"{gender} voice missing id: {v.get('name','?')}")
        if not v.get("name"):
            errs.append(f"{gender} voice missing name: {v.get('id','?')}")
        ids[v.get("id")] = v.get("name")

# every chosen ID must exist in the registry
for role, vid in d.get("chosen", {}).items():
    if vid not in ids:
        errs.append(f"chosen.{role} = {vid!r} not found in voices.female/male")

# voice_settings sanity
vs = d.get("voice_settings", {})
for k in ("stability", "similarity_boost", "style"):
    if k in vs and not (0.0 <= float(vs[k]) <= 1.0):
        errs.append(f"voice_settings.{k} out of [0,1]: {vs[k]}")

if errs:
    print("voices_de.json INVALID:")
    for e in errs:
        print("  -", e)
    sys.exit(1)
nf, nm = len(voices.get("female", [])), len(voices.get("male", []))
print(f"voices_de.json OK — {nf} female + {nm} male voices; chosen all resolve "
      f"({', '.join(d['chosen'])}).")
PY
