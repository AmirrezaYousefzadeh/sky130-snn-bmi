#!/usr/bin/env bash
# Idle-window power of an already processed SoC waveform (power/out_soc_<tag>/window.json exists). Usage: soc_idle_window.sh <vcd> <run> <period_ns> <tag>
set -euo pipefail; ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"; VCD="$1"; RUN="$2"; P="$3"; TAG="$4"; OUT="$ROOT/power/out_soc_$TAG"
IB=$(python3 -c "import json;d=json.load(open('$OUT/window.json'));ts={'1ns':1e-9,'1ps':1e-12,'100ps':1e-10,'10ps':1e-11}[d['timescale']];print(int(d['begin']-9000*$P*1e-9/ts))")
IE=$(python3 -c "import json;d=json.load(open('$OUT/window.json'));ts={'1ns':1e-9,'1ps':1e-12,'100ps':1e-10,'10ps':1e-11}[d['timescale']];print(int(d['begin']-1000*$P*1e-9/ts))")
mkdir -p "$OUT/idle"; "$ROOT/tools/vcd_toggles" -o "$OUT/idle/toggles.tsv" --begin "$IB" --end "$IE" "$VCD" 2> "$OUT/idle/toggles.log"
RUN_DIR="$RUN" PERIOD_NS="$P" LIB_SRAM="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" "$ROOT/power/run_toggles_power.sh" riscv "$OUT/idle/toggles.tsv" "$OUT/idle/pwr" > "$OUT/idle/pwr.log" 2>&1 || tail -3 "$OUT/idle/pwr.log"
echo "-- $TAG idle (8,000 sleep cycles, clock running): $(grep -E "^Total" "$OUT/idle/pwr/power_vcd.rpt" | head -n 1)"
