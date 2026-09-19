#!/usr/bin/env bash
# Round 5: liberty re-evaluations of the 5 MHz sky130 waveforms: ss_n40C_1v28 (E5 low-voltage row, f_max) on the 500-bin and idle
# runs, tt_100C_1v80 on the idle run (leakage at 100 C for the 37 C interpolation of figure F3). Usage: corners5.sh <design>...
cd "$(dirname "$0")/.."
for D in "$@"; do
  RT="${D}_5m"; R="$PWD/synthesis/$D/runs/$RT"; [[ -f "$R/final/metrics.json" ]] || { echo "$D: no 5 MHz run"; continue; }
  for t in md0_full idle_full; do
    [[ -f "sim/build_${RT}_$t/${RT}_$t.vcd" ]] || continue
    [[ -f "power/out_vcd_${RT}_${t}_ss_n40C_1v28/power_vcd.rpt" ]] || RUN_DIR="$R" PERIOD_NS=200 ./power/run_corner_power.sh "$D" "${RT}_$t" ss_n40C_1v28 > "logs/corner_${RT}_${t}_1v28.log" 2>&1
  done
  [[ -f "power/out_vcd_${RT}_idle_full_tt_100C_1v80/power_vcd.rpt" || ! -f "sim/build_${RT}_idle_full/${RT}_idle_full.vcd" ]] || RUN_DIR="$R" PERIOD_NS=200 ./power/run_corner_power.sh "$D" "${RT}_idle_full" tt_100C_1v80 > "logs/corner_${RT}_idle_100C.log" 2>&1
  echo "$D: $(grep -h '^Total' power/out_vcd_${RT}_md0_full_ss_n40C_1v28/power_vcd.rpt 2>/dev/null | head -n 1 | cut -c1-90) | 100C leak: $(grep -h '^Total' power/out_vcd_${RT}_idle_full_tt_100C_1v80/power_vcd.rpt 2>/dev/null | awk '{print $3}')"
done
