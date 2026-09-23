#!/usr/bin/env bash
# Round 5 (E14): energy of the low-voltage signoff hardening (<design>_5m_lv, synthesis/harden_lowv.sh) at its signoff corner:
# SDF of nom_ss_n40C_1v28 annotated on the netlist, 200 bins of indy_20160630_01 back-to-back, per-pin power with the
# ss_n40C_1v28 liberty (tag <design>_5m_lv_md0_sdf), plus the zero-delay 500-bin run at the same corner (tag ..._md0_full) and the
# idle run (leakage at 1.28 V, -40 C). Usage: sim/measure_lowv.sh <design>
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"; RT="${D}_5m_lv"; RUN="$ROOT/synthesis/$D/runs/$RT"
while [[ ! -e "$RUN/final/metrics.json" ]]; do sleep 300; done
LIB=/media/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_n40C_1v28.lib
case "$D" in
  bmi_snn_sp)    INC=$ROOT/rtl/sp;  VEC=$ROOT/sim/vec_sp_indy_20160630_01 ;;
  bmi_snn_m12)   INC=$ROOT/rtl;     VEC=$ROOT/sim/vec_v12_indy_20160630_01 ;;
  bmi_snn_min32) INC=$ROOT/rtl/h32; VEC=$ROOT/sim/vec_h32_indy_20160630_01 ;;
  bmi_snn_g32p50) INC=$ROOT/rtl/g32p50; VEC=$ROOT/sim/vecfull_g32p50_indy_20160630_01 ;;   # round 6 (E4b): the H = 32 / 50 % grid core (first bins of its full-block vectors)
  *) echo "unknown $D"; exit 2 ;;
esac
SDF="$(find "$RUN/final/sdf/nom_ss_n40C_1v28" -name '*.sdf' 2>/dev/null | head -n 1)"
run() { # tag nbins gap sdf|nosdf
  local tag=$1 nb=$2 gap=$3 extra=""; [[ $4 == nosdf ]] && extra="--no-sdf"
  echo "==== E14 $D $tag ($(date +%H:%M:%S))"
  INCDIR=$INC DESIGN=$D DUT=$D LOAD="" RUN_DIR=$RUN SDF_SRC="$SDF" TAG=$tag DUMP_LEVEL=0 CLK_NS=200 EXTRA_DEFS="-DTIMEOUT_CYCLES=2000000000" \
    "$ROOT/sim/run_gls_stream.sh" "$VEC" $nb 0 $gap $extra > "$ROOT/logs/$tag.log" 2>&1 || { tail -5 "$ROOT/logs/$tag.log"; return 1; }
  grep -E "SUMMARY|PASS|FAIL|SDF:" "$ROOT/logs/$tag.log" | head -n 3
  DESIGN=$D MACRO_INST=none PERIOD_NS=200 RUN_DIR=$RUN LIB_SC=$LIB "$ROOT/power/run_toggles_power.sh" core "$ROOT/sim/build_$tag/toggles.tsv" "$ROOT/power/out_vcd_$tag" > "$ROOT/logs/power_$tag.log" 2>&1 || { tail -5 "$ROOT/logs/power_$tag.log"; return 1; }
  grep -E "^Total|WORST_SETUP" "$ROOT/power/out_vcd_$tag/power_vcd.rpt" "$ROOT/power/out_vcd_$tag/sta.log" | head -n 2
}
run ${RT}_md0_full 500 0 nosdf; run ${RT}_idle_full 1 400000 nosdf
[[ -n "$SDF" ]] && run ${RT}_md0_sdf 200 0 sdf || echo "no SDF at nom_ss_n40C_1v28 in $RUN"
# the tt-signoff 5 MHz netlist evaluated at the same corner (as Table A2 did at 50 MHz): activity of its annotated 200-bin run, ss_n40C_1v28 liberty
if [[ -f "$ROOT/sim/build_${D}_5m_md0_sdf/${D}_5m_md0_sdf.vcd" ]]; then
  RUN_DIR="$ROOT/synthesis/$D/runs/${D}_5m" PERIOD_NS=200 "$ROOT/power/run_corner_power.sh" "$D" "${D}_5m_md0_sdf" ss_n40C_1v28 > "$ROOT/logs/corner_${D}_5m_ss_n40C_1v28.log" 2>&1 && grep -E "^Total|WORST" "$ROOT/power/out_vcd_${D}_5m_md0_sdf_ss_n40C_1v28/power_vcd.rpt" "$ROOT/power/out_vcd_${D}_5m_md0_sdf_ss_n40C_1v28/sta.log" | head -n 2
fi
echo "==== E14 $D done ($(date +%H:%M:%S))"
