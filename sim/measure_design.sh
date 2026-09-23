#!/usr/bin/env bash
# Complete energy measurement set for one core variant.
# Usage: ./sim/measure_design.sh <design> [func|sdf]      design: any name in sw/gen_variant.py or bmi_snn_top
#  func: zero-delay functional GLS, full-depth dump: event 500 bins back-to-back, dense 100 bins, idle 1 bin + 400k idle cycles
#  sdf : SDF-annotated GLS (glitches), full-depth dump: event 200 bins, dense 40 bins, idle 1 bin + 100k idle cycles
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$1"; KIND="${2:-func}"
RUN_TAG="${RUN_TAG:-$D}"; CLK_NS="${CLK_NS:-20}"          # round 5: RUN_TAG=<design>_5m CLK_NS=200 selects the 5 MHz hardening and its tags
export RUN_DIR="$ROOT/synthesis/$D/runs/$RUN_TAG"
case "$D" in
  bmi_snn_top|bmi_snn_topg) LOAD="-DLOAD_BACKDOOR"; MACRO="u_wmem" ;;
  bmi_snn_hw|bmi_snn_min|bmi_snn_ming) LOAD=""; MACRO="none" ;;
  bmi_snn_m12)   LOAD=""; MACRO="none"; VECSEL="vec_v12_indy_20160630_01" ;;
  bmi_snn_sp)    LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/sp"; VECSEL="vec_sp_indy_20160630_01" ;;
  bmi_snn_sp8)   LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/sp8"; VECSEL="vec_sp8_indy_20160630_01" ;;
  bmi_snn_lmem|bmi_snn_lmem2) LOAD="-DLOAD_PORT -DDUMP_AFTER_LOAD -DHAS_WR_READY"; MACRO="none" ;;
  bmi_snn_lmin|bmi_snn_lmin2) LOAD="-DLOAD_PORT -DDUMP_AFTER_LOAD -DHAS_WR_READY"; MACRO="none"; VECSEL="vec_v12_indy_20160630_01" ;;
  bmi_snn_min32) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/h32"; VECSEL="vec_h32_indy_20160630_01" ;;
  bmi_snn_min16) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/h16"; VECSEL="vec_h16_indy_20160630_01" ;;
  bmi_snn_scmem) LOAD="-DLOAD_PORT -DDUMP_AFTER_LOAD -DHAS_WR_READY"; MACRO="none" ;;
  bmi_snn_g128|bmi_snn_g128p25|bmi_snn_g128p125|bmi_snn_g64p50|bmi_snn_g64p125|bmi_snn_g32p50|bmi_snn_g32p25|bmi_snn_g16p50|bmi_snn_g48|bmi_snn_g48p50|bmi_snn_g48p25|bmi_snn_g32p125)   # round 5 (E2): training grid, hardwired 12-bit gated
                 LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/${D#bmi_snn_}"; VECSEL="vecfull_${D#bmi_snn_}_indy_20160630_01" ;;
  bmi_snn_sp_s622)    LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/sp_s622";  VECSEL="vecfull_sp_indy_20160622_01" ;;    # round 5 (E3): per-session netlists
  bmi_snn_sp_s131)    LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/sp_s131";  VECSEL="vecfull_sp_indy_20170131_02" ;;
  bmi_snn_min32_s622) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/h32_s622"; VECSEL="vecfull_h32_indy_20160622_01" ;;
  bmi_snn_min32_s131) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/h32_s131"; VECSEL="vecfull_h32_indy_20170131_02" ;;
  bmi_snn_g32p50_s622) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/g32p50_s622"; VECSEL="vecfull_g32p50_s622_indy_20160622_01" ;;   # round 6 (E4a)
  bmi_snn_g32p50_s131) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/g32p50_s131"; VECSEL="vecfull_g32p50_s131_indy_20170131_02" ;;
  bmi_snn_m12_s622)   LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/m12_s622"; VECSEL="vecfull_v12_indy_20160622_01" ;;
  bmi_snn_m12_s131)   LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/m12_s131"; VECSEL="vecfull_v12_indy_20170131_02" ;;
  *) echo "unknown design $D"; exit 2 ;;
esac
# SDF annotation of the standard-cell weight memories (370k-600k instances) does not complete in Icarus within hours; skip
case "$D:$KIND" in bmi_snn_scmem:sdf|bmi_snn_lmem:sdf|bmi_snn_lmin:sdf|bmi_snn_lmem2:sdf|bmi_snn_lmin2:sdf) echo "==== $D sdf skipped (SDF annotation of this netlist size does not complete; functional energy is reported)"; echo "==== $D sdf done (skipped)"; exit 0;; esac
if [[ "$KIND" == "func" ]]; then EXTRA="--no-sdf"; NEV=500; NDN=100; NIDLE=400000; SUF="full"; else EXTRA=""; NEV=200; NDN=40; NIDLE=100000; SUF="sdf"; fi
if [[ "$D" == "bmi_snn_top" && "$KIND" == "func" && "$RUN_TAG" == "$D" ]]; then T_EV=gls_md0_full; T_DN=gls_md1_full; T_ID=gls_idle2_full; else T_EV=${RUN_TAG}_md0_$SUF; T_DN=${RUN_TAG}_md1_$SUF; T_ID=${RUN_TAG}_idle_$SUF; fi
VEC="$ROOT/sim/${VECSEL:-vec_indy_20160630_01}"
run_one() { # tag nbins mode gap
  local tag=$1 nb=$2 md=$3 gap=$4
  echo "==== $D $KIND $tag ($(date +%H:%M:%S))"
  DESIGN=$D DUT=$D LOAD="$LOAD" DUMP_LEVEL=0 TAG=$tag CLK_NS=$CLK_NS "$ROOT/sim/run_gls.sh" "$VEC" $nb $md $gap $EXTRA > "$ROOT/logs/$tag.log" 2>&1 || { tail -5 "$ROOT/logs/$tag.log"; return 1; }
  grep -E "SUMMARY|MEASURED|PASS|FAIL|real|VCD:" "$ROOT/logs/$tag.log"
  DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN_DIR" "$ROOT/power/run_vcd_power.sh" core "$ROOT/sim/build_$tag/$tag.vcd" > "$ROOT/logs/vcd_power_$tag.log" 2>&1 || { tail -5 "$ROOT/logs/vcd_power_$tag.log"; return 1; }
  grep -E "Annotated|^Total" "$ROOT/logs/vcd_power_$tag.log" "$ROOT/power/out_vcd_$tag/power_vcd.rpt" | head -3
}
run_one $T_EV $NEV 0 0 &
case "$D" in bmi_snn_min|bmi_snn_min32|bmi_snn_min16|bmi_snn_ming|bmi_snn_m12|bmi_snn_sp|bmi_snn_sp8|bmi_snn_lmin|bmi_snn_lmin2|bmi_snn_g*|bmi_snn_*_s622|bmi_snn_*_s131) ;; *) run_one $T_DN $NDN 1 0 & ;; esac   # DENSE=0 cores have no dense mode
run_one $T_ID 1 0 $NIDLE &
wait
echo "==== $D $KIND done ($(date +%H:%M:%S))"
