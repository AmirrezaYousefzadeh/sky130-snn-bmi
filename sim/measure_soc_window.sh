#!/usr/bin/env bash
# Round 5 (E7): per-pin OpenSTA power of the RISC-V SoC over the decoding window of a stored gate-level VCD (last wake before
# gpio_done .. gpio_done), with the streamed toggle accumulation restricted to that window.
# Usage: measure_soc_window.sh <vcd> <soc_run_dir> <period_ns> <out_tag> [n_bins=16]
# Output: power/out_soc_<tag>/{window.json,toggles.tsv,pwr/power_vcd.rpt (vdd-only SRAM liberty),asgen/power_vcd.rpt (as-generated liberty)}
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"
VCD="$1"; RUN="$2"; P="$3"; TAG="$4"; NB="${5:-16}"
OUT="$ROOT/power/out_soc_$TAG"; mkdir -p "$OUT"
echo "==== SoC window $TAG: $VCD ($(date +%H:%M:%S))"
python3 "$ROOT/sw/riscv_window.py" "$VCD" "$NB" > "$OUT/window.json"
B=$(python3 -c "import json;print(json.load(open('$OUT/window.json'))['begin'])"); E=$(python3 -c "import json;print(json.load(open('$OUT/window.json'))['end'])")
python3 -c "import json;d=json.load(open('$OUT/window.json'));print('window', d['begin'], d['end'], d['timescale'], 'cycles', d['cycles_in_window'], 'awake', d['awake_cycles_in_window'], 'cyc/bin', d['cycles_per_bin'])"
( time "$ROOT/tools/vcd_toggles" -o "$OUT/toggles.tsv" --begin "$B" --end "$E" "$VCD" ) 2>&1 | tail -n 4
for L in pwr asgen; do
  if [[ $L == pwr ]]; then LIB="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib"; else LIB="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80.lib"; fi
  RUN_DIR="$RUN" PERIOD_NS="$P" LIB_SRAM="$LIB" "$ROOT/power/run_toggles_power.sh" riscv "$OUT/toggles.tsv" "$OUT/$L" > "$OUT/$L.log" 2>&1 || { tail -5 "$OUT/$L.log"; exit 1; }
  echo "-- $L: $(grep -E "^Total" "$OUT/$L/power_vcd.rpt" | head -n 1)"
done
# idle window (round 5, E7): the 10,000-cycle sleep before the decoding wake (sram_clk_en low, clock running) -> idle power with the clock on
IB=$(python3 -c "import json;d=json.load(open('$OUT/window.json'));ts={'1ns':1e-9,'1ps':1e-12,'100ps':1e-10,'10ps':1e-11}[d['timescale']];print(int(d['begin']-9000*$P*1e-9/ts))")
IE=$(python3 -c "import json;d=json.load(open('$OUT/window.json'));ts={'1ns':1e-9,'1ps':1e-12,'100ps':1e-10,'10ps':1e-11}[d['timescale']];print(int(d['begin']-1000*$P*1e-9/ts))")
mkdir -p "$OUT/idle"; "$ROOT/tools/vcd_toggles" -o "$OUT/idle/toggles.tsv" --begin "$IB" --end "$IE" "$VCD" 2> "$OUT/idle/toggles.log"
RUN_DIR="$RUN" PERIOD_NS="$P" LIB_SRAM="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" "$ROOT/power/run_toggles_power.sh" riscv "$OUT/idle/toggles.tsv" "$OUT/idle/pwr" > "$OUT/idle/pwr.log" 2>&1 || tail -3 "$OUT/idle/pwr.log"
echo "-- idle (8,000 sleep cycles, clock running): $(grep -E "^Total" "$OUT/idle/pwr/power_vcd.rpt" | head -n 1)"
echo "==== SoC window $TAG done ($(date +%H:%M:%S))"
