#!/usr/bin/env bash
# Hermetic self-test for qualtrics-export-coverage-audit.
# Exercises audit_export_coverage.py against fixtures/survey_def_sample.json:
#   - healthy_q + f_ty_room_N_t1_time → in a flow-reached block → MUST export
#   - blockless_q                     → in no block             → MUST be flagged
#   - unreached_q                     → block not in flow       → MUST be flagged
# Exit 0 on pass, non-zero on any divergence.
set -u
cd "$(dirname "$0")" || exit 2
PY="$(command -v python3)"

out="$("$PY" audit_export_coverage.py --json fixtures/survey_def_sample.json 2>&1)"
rc=$?
fail() { echo "FAIL: $1"; echo "--- output ---"; echo "$out"; exit 1; }

# Default run must FAIL (exit 1) because two tags silently drop.
[ "$rc" -eq 1 ] || fail "expected exit 1 on a survey with non-exporting tags, got $rc"
echo "$out" | grep -q "blockless_q .* block-less"              || fail "blockless_q not flagged block-less"
echo "$out" | grep -q "unreached_q .* not in flow"             || fail "unreached_q not flagged unreached"
echo "$out" | grep -q "healthy_q"                              && fail "healthy_q wrongly flagged"
echo "$out" | grep -q "f_ty_room_N_t1_time"                    && fail "flow-reached f_ty_room tag wrongly flagged"

# --expect-missing whitelist must flip the exit code back to 0.
out="$("$PY" audit_export_coverage.py --json fixtures/survey_def_sample.json \
        --expect-missing blockless_q,unreached_q 2>&1)"
rc=$?
[ "$rc" -eq 0 ] || fail "expected exit 0 when all non-exporters are whitelisted, got $rc"
echo "$out" | grep -q "(expected)" || fail "whitelisted tags not marked (expected)"

# --prefix narrows scope: the f_ty_room family alone all export → PASS.
out="$("$PY" audit_export_coverage.py --json fixtures/survey_def_sample.json \
        --prefix f_ty_room 2>&1)"
rc=$?
[ "$rc" -eq 0 ] || fail "expected exit 0 for the all-exporting f_ty_room prefix, got $rc"
echo "$out" | grep -q "PASS" || fail "prefix scope did not report PASS"

echo "PASS: qualtrics-export-coverage-audit runner — block-less + unreached flagged, healthy clean, whitelist + prefix honoured."
