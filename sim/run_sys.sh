#!/usr/bin/env bash
# Round 6 (E6): gate-level co-simulation of the front end and the pruned core (rtl/bmi_sys.v over the routed netlists of bmi_fe and
# bmi_snn_sp), recorded stream of indy_20160630_01 in real time at 250 bins/s. Usage: run_sys.sh <n_bins> [--stream]
#   --stream: dump the whole system through a FIFO into tools/vcd_toggles (per-pin toggle counts for OpenSTA), no waveform stored.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"; PDK_ROOT="${PDK_ROOT:-/media/pdk}"; LIB=sky130_fd_sc_hd
NB="${1:-500}"; MODE="${2:-}"; VEC="${VEC:-$ROOT/sim/vec_sp_indy_20160630_01}"; TAG="${TAG:-sys_sp_gls}"
FE_NL="${FE_NL:-$ROOT/synthesis/bmi_fe/runs/bmi_fe_5m/final/nl/bmi_fe.nl.v}"; CORE_NL="${CORE_NL:-$ROOT/synthesis/bmi_snn_sp/runs/bmi_snn_sp_5m/final/nl/bmi_snn_sp.nl.v}"
OUT="$ROOT/sim/build_$TAG"; rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
DEFS=(-DN_BINS=$NB -DSTREAM_HEX="\"$VEC/stream.hex\"" -DEXPECT_HEX="\"$VEC/expect.hex\"" -DFUNCTIONAL -DUNIT_DELAY='#1' ${EXTRA_DEFS:-})
[[ "$MODE" == "--stream" ]] && { FIFO="$OUT/$TAG.vcd"; mkfifo "$FIFO"; DEFS+=(-DDUMP_PATH="\"$FIFO\""); }
SRCS=("$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/primitives.v" "$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/$LIB.v" "$FE_NL" "$CORE_NL" "$ROOT/rtl/bmi_sys.v" "$ROOT/sim/tb_bmi_sys.v")
iverilog -g2012 -o sys.vvp "${DEFS[@]}" "${SRCS[@]}" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
if [[ "$MODE" == "--stream" ]]; then "$ROOT/tools/vcd_toggles" -o "$OUT/toggles.tsv" "$FIFO" 2> toggles.log & TPID=$!; fi
echo "==> running $TAG ($NB bins, $(date +%H:%M:%S))"; ( time vvp -n sys.vvp ) > vvp.log 2>&1 || true
[[ "$MODE" == "--stream" ]] && { wait $TPID; rm -f "$FIFO"; cat toggles.log; }
grep -E "SUMMARY|PASS|FAIL|MISMATCH|real" vvp.log | head -n 12
