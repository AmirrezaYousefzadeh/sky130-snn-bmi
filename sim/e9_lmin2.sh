#!/usr/bin/env bash
# Round 5 (E9): annotated glitch factor of the latch-memory core bmi_snn_lmin2 (and lmem2 if hardened) at 5 MHz on >= 50 bins:
# SDF-annotated streamed run of the first 50 bins of indy_20160630_01 and the zero-delay run of the same window. 48 h budget each.
# Usage: sim/e9_lmin2.sh [design=bmi_snn_lmin2] [n_bins=50]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="${1:-bmi_snn_lmin2}"; NB="${2:-50}"
export RUN_TAG="${D}_5m" CLK_NS=200
while [[ ! -e "$ROOT/synthesis/$D/runs/${RUN_TAG}/final/metrics.json" ]]; do sleep 300; done
echo "==== E9 $D: $NB bins zero-delay then annotated ($(date +%H:%M))"
[[ -f "$ROOT/power/out_${RUN_TAG}_func_w${NB}_indy_20160630_01/power_vcd.rpt" ]] || timeout 48h "$ROOT/sim/measure_full.sh" "$D" indy_20160630_01 func "$NB"
[[ -f "$ROOT/power/out_${RUN_TAG}_sdf_w${NB}_indy_20160630_01/power_vcd.rpt" ]] || timeout 48h "$ROOT/sim/measure_full.sh" "$D" indy_20160630_01 sdf "$NB"
echo "==== E9 $D done ($(date +%H:%M))"
