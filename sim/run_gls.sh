#!/usr/bin/env bash
# Gate-level simulation (SDF by default) of the hardened bmi_snn_top -> VCD for power.
# Usage: ./sim/run_gls.sh <vector_dir> <n_bins> <mode_dense> [idle_gap] [--no-sdf]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SIM="$ROOT/sim"
export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"
PDK_ROOT="${PDK_ROOT:-/media/pdk}"; LIB=sky130_fd_sc_hd
DESIGN="${DESIGN:-bmi_snn_top}"; DUT="${DUT:-bmi_snn_top}"; LOAD="${LOAD--DLOAD_BACKDOOR}"; CLK_NS="${CLK_NS:-20}"
RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$DESIGN/runs/$DESIGN}"
VEC="$(cd "$1" && pwd)"; NB="$2"; MD="$3"; GAP="${4:-64}"; NOSDF="${5:-}"
NETLIST="$RUN_DIR/final/nl/$DESIGN.nl.v"
SDF_SRC="$(find "$RUN_DIR/final/sdf/nom_tt_025C_1v80" -name '*.sdf' | head -1)"
TAG="${TAG:-gls_md${MD}}"
OUT="$SIM/build_${TAG}"; rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
VCD="$OUT/${TAG}.vcd"
DEFS=(-DGLS -DGLS_PROGRESS -DN_BINS="$NB" -DMODE_DENSE="$MD" -DIDLE_GAP="$GAP" -DDUT="$DUT" $LOAD -DCLK_PERIOD_NS="$CLK_NS" ${EXTRA_DEFS:-}
      -DSTREAM_HEX="\"$VEC/stream.hex\"" -DEXPECT_HEX="\"$VEC/expect.hex\"" -DWEIGHTS_HEX="\"$VEC/weights.hex\""
      -DSTAT_FILE="\"$OUT/stats.txt\"" -DDUMP_PATH="\"$VCD\"" -DDUMP_LEVEL="${DUMP_LEVEL:-1}" -DDUMP_MODULE=tb_bmi_snn.u_dut)
FLAGS=(-g2012)
SRCS=("$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/primitives.v")
if [[ "$NOSDF" == "--no-sdf" ]]; then
  DEFS+=(-DFUNCTIONAL -DUNIT_DELAY='#1')
else
  python3 "$SIM/sdf_sanitize_for_icarus.py" "$SDF_SRC" -o "$OUT/design.icarus.sdf"
  DEFS+=(-DUNIT_DELAY='#1' -DSDF_ANNOTATE="\"$OUT/design.icarus.sdf\"")
  FLAGS+=(-gspecify -ginterconnect -Ttyp)
  SRCS+=("$SIM/sky130_timing_icarus_fixes.v")
fi
# SDF runs: the sanitised SDF has no macro delays, so give the behavioural SRAM a realistic clock-to-output delay
if [[ "$NOSDF" == "--no-sdf" ]]; then SRAM_V="$ROOT/../skywater/rtl/sram/sram22_2048x32m8w8.v"; else SRAM_V="$SIM/sram22_2048x32m8w8_tdout.v"; fi
SRCS+=("$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/$LIB.v" "$SRAM_V" "$NETLIST" "$SIM/tb_bmi_snn.v")
echo "==> compiling GLS ($TAG)"; iverilog "${FLAGS[@]}" -I "${INCDIR:-$ROOT/rtl}" -o gls.vvp "${DEFS[@]}" "${SRCS[@]}" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
echo "==> running ($(date +%H:%M:%S))"; ( time vvp -n gls.vvp ) > vvp.log 2>&1 || true
grep -E "SUMMARY|PASS|FAIL|MISMATCH|SDF:" vvp.log | head -20; tail -3 vvp.log
python3 "$SIM/vcd_rescale_ns.py" "$VCD" >/dev/null
if [[ "${LOAD:-} ${EXTRA_DEFS:-}" == *DUMP_AFTER_LOAD* ]]; then python3 "$SIM/vcd_shift_time.py" "$VCD"; fi
echo "VCD: $VCD ($(du -h "$VCD" | cut -f1))"
