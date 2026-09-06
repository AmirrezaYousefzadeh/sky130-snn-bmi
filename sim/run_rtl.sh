#!/usr/bin/env bash
# RTL simulation of bmi_snn_top with Icarus.  Usage: run_rtl.sh <vector_dir> <n_bins> [mode_dense] [idle_gap] [--vcd]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"
VEC="$(cd "$1" && pwd)"; NB="$2"; MD="${3:-0}"; GAP="${4:-64}"; VCD="${5:-}"
OUT="$ROOT/sim/build_rtl"; mkdir -p "$OUT"; cd "$OUT"
DUMP=()
if [[ "$VCD" == "--vcd" ]]; then DUMP=(-DDUMP_PATH="\"$OUT/rtl_md${MD}.vcd\"" -DDUMP_LEVEL=1 -DDUMP_MODULE=tb_bmi_snn.u_dut); fi
DUT="${DUT:-bmi_snn_top}"; RTL="${RTL:-$ROOT/rtl/bmi_snn_top.v}"; LOAD="${LOAD--DLOAD_BACKDOOR}"
iverilog -g2012 -I "${INCDIR:-$ROOT/rtl}" -o tb_md${MD}.vvp -DN_BINS="$NB" -DMODE_DENSE="$MD" -DIDLE_GAP="$GAP" -DDUT="$DUT" $LOAD ${EXTRA_DEFS:-} \
  -DSTREAM_HEX="\"$VEC/stream.hex\"" -DEXPECT_HEX="\"$VEC/expect.hex\"" -DWEIGHTS_HEX="\"$VEC/weights.hex\"" \
  -DSTAT_FILE="\"$OUT/stats_md${MD}.txt\"" "${DUMP[@]}" \
  "$ROOT/sim/sky130_hd_dlclkp_stub.v" "$ROOT/rtl/clk_gate_hd.v" \
  "$ROOT/../skywater/rtl/sram/sram22_2048x32m8w8.v" $RTL "$ROOT/sim/tb_bmi_snn.v"
vvp -n tb_md${MD}.vvp | grep -v "^VCD info" | tail -n 15
