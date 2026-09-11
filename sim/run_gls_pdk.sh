#!/usr/bin/env bash
# Functional gate-level simulation of a hardwired core hardened on another PDK (multi-PDK study).
# Usage: PDK_VERILOG="<cell models .v ...>" INCDIR=rtl/h16 DESIGN=bmi_snn_min16 DUT=bmi_snn_min16 NETLIST=<final/nl/*.nl.v> TAG=<tag> \
#        ./sim/run_gls_pdk.sh <vector_dir> <n_bins> <mode_dense> [idle_gap]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SIM="$ROOT/sim"
export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"
VEC="$(cd "$1" && pwd)"; NB="$2"; MD="$3"; GAP="${4:-0}"
OUT="$SIM/build_${TAG}"; rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
VCD="$OUT/${TAG}.vcd"
DEFS=(-DGLS -DGLS_PROGRESS -DFUNCTIONAL -DUNIT_DELAY='#1' -DN_BINS="$NB" -DMODE_DENSE="$MD" -DIDLE_GAP="$GAP" -DDUT="$DUT" -DCLK_PERIOD_NS="${CLK_NS:-20}"
      -DSTREAM_HEX="\"$VEC/stream.hex\"" -DEXPECT_HEX="\"$VEC/expect.hex\"" -DWEIGHTS_HEX="\"$VEC/weights.hex\""
      -DSTAT_FILE="\"$OUT/stats.txt\"" -DDUMP_PATH="\"$VCD\"" -DDUMP_LEVEL="${DUMP_LEVEL:-0}" -DDUMP_MODULE=tb_bmi_snn.u_dut ${EXTRA_DEFS:-})
echo "==> compiling GLS ($TAG) with $(echo $PDK_VERILOG | wc -w) model file(s)"
iverilog -g2012 -I "${INCDIR:-$ROOT/rtl}" -o gls.vvp "${DEFS[@]}" $PDK_VERILOG "$NETLIST" "$SIM/tb_bmi_snn.v" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
echo "==> running ($(date +%H:%M:%S))"; ( time vvp -n gls.vvp ) > vvp.log 2>&1 || true
grep -E "SUMMARY|PASS|FAIL|MISMATCH" vvp.log | head -5; tail -2 vvp.log
python3 "$SIM/vcd_rescale_ns.py" "$VCD" >/dev/null
echo "VCD: $VCD ($(du -h "$VCD" | cut -f1))"
