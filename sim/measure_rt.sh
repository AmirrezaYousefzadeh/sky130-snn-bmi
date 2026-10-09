#!/usr/bin/env bash
# Round 10 (E6): real-time power measurement of one sky130 core. The testbench (sim/tb_bmi_snn.v, -DREALTIME) presents bin k at
# t = k x 4 ms, one event at a time through the handshake, the tick after the last event; the 5 MHz clock runs from the bin start
# until the core is idle again and is stopped for the rest of the bin. The toggles of every pin over the whole window T = N x 4 ms
# (idle gaps included) are converted to per-pin activities (power/toggles_to_activity.py) and OpenSTA reports the average power on
# the routed netlist with its parasitics (power/run_toggles_power.sh). A second OpenSTA run with all data activities zero gives the
# clock-driven power of the root clock network (clock port -> first clock gate), which OpenSTA charges at the full clock rate; the
# root-clock correction (power/root_clock_correction.py) scales it by the measured duty of the clock port.
# Usage: RUN_TAG=<design>_5m ./sim/measure_rt.sh <design> <sdf|func> <n_bins> [dense=0] [session=indy_20160630_01]
# Output: sim/build_rt_<design>_<kind>_md<d>_w<N>_<session>/, power/out_rt_<...>/ (+ _zero), logs/rt_<...>.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$1"; KIND="$2"; NB="$3"; MD="${4:-0}"; S="${5:-indy_20160630_01}"
RUN_TAG="${RUN_TAG:-${D}_5m}"; CLK_NS="${CLK_NS:-200}"; export RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$D/runs/$RUN_TAG}"
LOAD=""; MACRO="none"; VP=""; export LIB_SRAM="${LIB_SRAM:-/nonexistent}"
case "$D" in
  bmi_snn_top|bmi_snn_topg) LOAD="-DLOAD_BACKDOOR"; MACRO="u_wmem"; export LIB_SRAM="$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" ;;   # vdd-only SRAM22 liberty (round 5)
  bmi_snn_hw|bmi_snn_hwg) ;;
  bmi_snn_scmem|bmi_snn_scmemg|bmi_snn_lmem|bmi_snn_lmem2|bmi_snn_lmem2g) LOAD="-DLOAD_PORT -DHAS_WR_READY" ;;
  bmi_snn_lmin|bmi_snn_lmin2) LOAD="-DLOAD_PORT -DHAS_WR_READY"; VP="v12_" ;;
  bmi_snn_min|bmi_snn_ming) VP="v16_" ;;
  bmi_snn_m12) VP="v12_" ;;
  bmi_snn_sp) export INCDIR="$ROOT/rtl/sp"; VP="sp_" ;;
  bmi_snn_min32|bmi_snn_min32g) export INCDIR="$ROOT/rtl/h32"; VP="h32_" ;;
  bmi_snn_g32) export INCDIR="$ROOT/rtl/h32"; VP="g32_" ;;
  bmi_snn_min16) export INCDIR="$ROOT/rtl/h16"; VP="h16_" ;;
  bmi_snn_g128|bmi_snn_g128p25|bmi_snn_g128p125|bmi_snn_g64p50|bmi_snn_g64p125|bmi_snn_g32p50|bmi_snn_g32p25|bmi_snn_g16p50|bmi_snn_g48|bmi_snn_g48p50|bmi_snn_g48p25|bmi_snn_g32p125) export INCDIR="$ROOT/rtl/${D#bmi_snn_}"; VP="${D#bmi_snn_}_" ;;
  *) echo "unknown design $D"; exit 2 ;;
esac
VEC="${VEC:-$ROOT/sim/vecfull_${VP}${S}}"; [[ -d "$VEC" ]] || { echo "no vectors $VEC"; exit 2; }
TOTAL=$(grep -c '^ff$' "$VEC/stream.hex"); [[ $NB -gt $TOTAL ]] && NB=$TOTAL
EXTRA=""; [[ "$KIND" == "func" ]] && EXTRA="--no-sdf"
TAG="rt_${RUN_TAG}_${KIND}_md${MD}_w${NB}_${S}"
echo "==== RT $D ($RUN_TAG) $KIND dense=$MD $S: $NB bins at 4 ms, clock $CLK_NS ns ($(date +%H:%M:%S))"
T0=$(date +%s)
DESIGN=$D DUT=$D LOAD="$LOAD" DUMP_LEVEL=0 TAG=$TAG CLK_NS=$CLK_NS EXTRA_DEFS="-DREALTIME -DTIMEOUT_CYCLES=2000000000 -DMAX_TOKENS=1400000 ${EXTRA_DEFS:-}" \
  "$ROOT/sim/run_gls_stream.sh" "$VEC" $NB $MD 0 $EXTRA > "$ROOT/logs/$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/$TAG.log"; exit 1; }
# --------------------------------------------------------
grep -E "SUMMARY|PASS|FAIL|RT:|real|vcd_toggles" "$ROOT/logs/$TAG.log"
echo "SIM_WALLCLOCK_S $(( $(date +%s) - T0 ))" >> "$ROOT/sim/build_$TAG/vvp.log"
grep -q "^PASS" "$ROOT/sim/build_$TAG/vvp.log" || { echo "simulation did not pass"; exit 1; }
OUT="$ROOT/power/out_$TAG"
export UNANNOTATED_ZERO=1
DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN_DIR" "$ROOT/power/run_toggles_power.sh" core "$ROOT/sim/build_$TAG/toggles.tsv" "$OUT" > "$ROOT/logs/power_$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/power_$TAG.log"; exit 1; }
GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN_DIR" "$ROOT/power/run_toggles_power.sh" core "$ROOT/sim/build_$TAG/toggles.tsv" "${OUT}_zero" > "$ROOT/logs/power_${TAG}_zero.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_zero.log"; exit 1; }
# duty of the clock port = delivered clock cycles / (window / period)
DUTY=$(python3 - "$ROOT/sim/build_$TAG/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s)
print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
NL="$RUN_DIR/final/nl/$D.nl.v"
python3 "$ROOT/power/root_clock_correction.py" "$NL" clk "$DUTY" "$OUT/power_vcd_by_instance.rpt" "${OUT}_zero/power_vcd_by_instance.rpt" -o "$OUT/root_clock_correction.json" | tail -5
grep -E "^Total" "$OUT/power_vcd.rpt"
echo "==== RT $TAG done ($(date +%H:%M:%S), $(( ($(date +%s) - T0) / 60 )) min)"
