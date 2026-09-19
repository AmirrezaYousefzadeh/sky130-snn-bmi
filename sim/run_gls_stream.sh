#!/usr/bin/env bash
# Gate-level simulation whose waveform is streamed through a FIFO into tools/vcd_toggles (per-pin transition counts and high
# times) instead of being stored: long windows (full test blocks) become tractable. Same arguments and environment as
# sim/run_gls.sh; output sim/build_<TAG>/toggles.tsv (+ vvp.log, stats.txt). Round 5, E4/E7.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SIM="$ROOT/sim"
export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"
PDK_ROOT="${PDK_ROOT:-/media/pdk}"; LIB=sky130_fd_sc_hd
DESIGN="${DESIGN:-bmi_snn_top}"; DUT="${DUT:-bmi_snn_top}"; LOAD="${LOAD--DLOAD_BACKDOOR}"; CLK_NS="${CLK_NS:-20}"
RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$DESIGN/runs/$DESIGN}"
VEC="$(cd "$1" && pwd)"; NB="$2"; MD="$3"; GAP="${4:-64}"; NOSDF="${5:-}"
NETLIST="${NETLIST:-$RUN_DIR/final/nl/$DESIGN.nl.v}"
TAG="${TAG:-gls_md${MD}}"
OUT="$SIM/build_${TAG}"; rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
FIFO="$OUT/${TAG}.vcd"; mkfifo "$FIFO"
DEFS=(-DGLS -DGLS_PROGRESS -DN_BINS="$NB" -DMODE_DENSE="$MD" -DIDLE_GAP="$GAP" -DDUT="$DUT" $LOAD -DCLK_PERIOD_NS="$CLK_NS" ${EXTRA_DEFS:-}
      -DSTREAM_HEX="\"$VEC/stream.hex\"" -DEXPECT_HEX="\"$VEC/expect.hex\"" -DWEIGHTS_HEX="\"$VEC/weights.hex\""
      -DSTAT_FILE="\"$OUT/stats.txt\"" -DDUMP_PATH="\"$FIFO\"" -DDUMP_LEVEL="${DUMP_LEVEL:-0}" -DDUMP_MODULE=tb_bmi_snn.u_dut)
FLAGS=(-g2012)
# PDK_VERILOG (round 5, E5): cell simulation models of another kit (space-separated files) replace the sky130 primitives and models
if [[ -n "${PDK_VERILOG:-}" ]]; then SRCS=($PDK_VERILOG); else SRCS=("$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/primitives.v"); fi
if [[ "$NOSDF" == "--no-sdf" ]]; then DEFS+=(-DFUNCTIONAL -DUNIT_DELAY='#1')
else
  SDF_SRC="${SDF_SRC:-$(find "$RUN_DIR/final/sdf/nom_tt_025C_1v80" -name '*.sdf' | head -1)}"
  python3 "$SIM/sdf_sanitize_for_icarus.py" "$SDF_SRC" -o "$OUT/design.icarus.sdf"
  DEFS+=(-DUNIT_DELAY='#1' -DSDF_ANNOTATE="\"$OUT/design.icarus.sdf\""); FLAGS+=(-gspecify -ginterconnect -Ttyp)
  [[ -z "${PDK_VERILOG:-}" ]] && SRCS+=("$SIM/sky130_timing_icarus_fixes.v")
fi
if [[ -z "${PDK_VERILOG:-}" ]]; then
  if [[ "$NOSDF" == "--no-sdf" ]]; then SRAM_V="$ROOT/../skywater/rtl/sram/sram22_2048x32m8w8.v"; else SRAM_V="$SIM/sram22_2048x32m8w8_tdout.v"; fi
  SRCS+=("$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/$LIB.v" "$SRAM_V")
fi
SRCS+=("$NETLIST" "$SIM/tb_bmi_snn.v")
echo "==> compiling GLS ($TAG, streamed)"; iverilog "${FLAGS[@]}" -I "${INCDIR:-$ROOT/rtl}" -o gls.vvp "${DEFS[@]}" "${SRCS[@]}" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
"$ROOT/tools/vcd_toggles" -o "$OUT/toggles.tsv" "$FIFO" 2> toggles.log & TPID=$!
echo "==> running ($(date +%H:%M:%S)), toggles accumulated by pid $TPID"; ( time vvp -n gls.vvp ) > vvp.log 2>&1 || true
wait $TPID; rm -f "$FIFO"
grep -E "SUMMARY|PASS|FAIL|MISMATCH|SDF:" vvp.log | head -20; tail -3 vvp.log; cat toggles.log
echo "TOGGLES: $OUT/toggles.tsv ($(wc -l < "$OUT/toggles.tsv") lines)"
