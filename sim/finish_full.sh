#!/usr/bin/env bash
# Round 5 (E4): power step of sim/measure_full.sh alone, for a streamed run whose toggles exist (e.g. after the driver script died).
# Usage: RUN_TAG=<design>_5m CLK_NS=200 ./sim/finish_full.sh <design> <tag>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"; TAG="$2"; RUN_TAG="${RUN_TAG:-${D}_5m}"; CLK_NS="${CLK_NS:-200}"
case "$D" in bmi_snn_top|bmi_snn_topg) MACRO="u_wmem" ;; *) MACRO="none" ;; esac
LIBS=""; [[ -n "${LIB_SRAM:-}" ]] && LIBS="LIB_SRAM=$LIB_SRAM"
OUT="$ROOT/power/out_$TAG"
grep -E "SUMMARY|PASS|FAIL" "$ROOT/sim/build_$TAG/vvp.log" | head -n 2
env $LIBS DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$ROOT/synthesis/$D/runs/$RUN_TAG" "$ROOT/power/run_toggles_power.sh" core "$ROOT/sim/build_$TAG/toggles.tsv" "$OUT" > "$ROOT/logs/power_$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/power_$TAG.log"; exit 1; }
grep -E "annotated|^Total" "$ROOT/logs/power_$TAG.log" "$OUT/power_vcd.rpt" | head -3; echo "==== $TAG done ($(date +%H:%M:%S))"
