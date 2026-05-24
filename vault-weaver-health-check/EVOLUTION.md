# Evolution log — vault-weaver-health-check

## 2026-05-24 — Skill created

Initial creation, derived from session patterns:

- **Index ↔ disk mismatch**: caused the "120 rejected in index but only 12
  files in rejected/" incident. The audit helper is the diagnostic that
  would have caught it immediately.
- **Ping-pongs**: the live-handler infinite-loop bug. Log analysis detects
  the signature (same slug, < 5s gap, reverse direction).
- **Tick freezes**: the >10s synchronous loops that froze Obsidian. Log
  analysis flags any tick > 10s as "UI freeze risk".
- **Healthy baseline ratio**: not yet locked in. Currently the analyzer
  reports raw net flow without comparing to a baseline; needs tuning once
  the user's real-world ratios stabilise.
