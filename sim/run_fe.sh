#!/usr/bin/env bash
# RTL or gate-level simulation of the digital front end (bmi_fe) on a recorded stream. Usage: run_fe.sh rtl|gls <n_bins> [--vcd]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"; PDK_ROOT="${PDK_ROOT:-/media/pdk}"; LIB=sky130_fd_sc_hd
MODE="$1"; NB="${2:-500}"; VCDF="${3:-}"; VEC="${VEC:-$ROOT/sim/vecfull_indy_20160630_01}"; RUN_TAG="${RUN_TAG:-bmi_fe_5m}"
OUT="$ROOT/sim/build_fe_${MODE}${TAG_SUFFIX:-}"; rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
DEFS=(-DN_BINS=$NB -DSTREAM_HEX="\"$VEC/stream.hex\"" ${EXTRA_DEFS:-}); [[ "$VCDF" == "--vcd" ]] && DEFS+=(-DDUMP_PATH="\"$OUT/fe_${MODE}.vcd\"")
if [[ "$MODE" == "rtl" ]]; then SRCS=("$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/primitives.v" "$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/$LIB.v" "$ROOT/rtl/bmi_fe.v"); DEFS+=(-DFUNCTIONAL -DUNIT_DELAY='#1')
else NL="$ROOT/synthesis/bmi_fe/runs/$RUN_TAG/final/nl/bmi_fe.nl.v"; SRCS=("$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/primitives.v" "$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/$LIB.v" "$NL"); DEFS+=(-DFUNCTIONAL -DUNIT_DELAY='#1'); fi
iverilog -g2012 -o fe.vvp "${DEFS[@]}" "${SRCS[@]}" "$ROOT/sim/tb_bmi_fe.v" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
( time vvp -n fe.vvp ) > vvp.log 2>&1 || true
grep -E "SUMMARY|PASS|FAIL|MISMATCH|real" vvp.log | head -n 12
[[ "$VCDF" == "--vcd" ]] && python3 "$ROOT/sim/vcd_rescale_ns.py" "$OUT/fe_${MODE}.vcd" > /dev/null && echo "VCD: $OUT/fe_${MODE}.vcd ($(du -h "$OUT/fe_${MODE}.vcd" | cut -f1))" || true
