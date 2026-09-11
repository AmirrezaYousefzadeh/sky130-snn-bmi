#!/usr/bin/env bash
# Referee experiments E1 (same-window glitch factor), E9 (energy transfer to the other sessions) and E5 (SDF on 500 bins for the
# small hardwired cores). Sequential: one gate-level simulation + one OpenSTA run at a time (the STA of a multi-GB VCD needs tens of GB).
cd "$(dirname "$0")/.."; ROOT=$PWD
rd() { case $1 in bmi_snn_min) echo $ROOT/synthesis/bmi_snn_min_lo/runs/bmi_snn_min_lo;; bmi_snn_hw) echo $ROOT/synthesis/bmi_snn_hw_lo/runs/bmi_snn_hw_lo;; *) echo $ROOT/synthesis/$1/runs/$1;; esac; }
cfg() { # design -> LOAD MACRO INCDIR
  case $1 in bmi_snn_top|bmi_snn_topg) echo "-DLOAD_BACKDOOR u_wmem $ROOT/rtl";; bmi_snn_sp) echo "- none $ROOT/rtl/sp";; bmi_snn_min32) echo "- none $ROOT/rtl/h32";; bmi_snn_min16) echo "- none $ROOT/rtl/h16";; *) echo "- none $ROOT/rtl";; esac; }
run() { # design tag vec nbins sdf(0/1)
  local d=$1 tag=$2 vec=$3 nb=$4 sdf=$5; read -r load macro inc <<< "$(cfg $d)"; [ "$load" = "-" ] && load=""
  local extra="--no-sdf"; [ "$sdf" = 1 ] && extra=""
  echo "==== $d $tag ($nb bins, sdf=$sdf) $(date +%H:%M)"
  DESIGN=$d DUT=$d LOAD="$load" DUMP_LEVEL=0 TAG=$tag CLK_NS=20 INCDIR=$inc RUN_DIR=$(rd $d) sim/run_gls.sh $vec $nb 0 0 $extra > logs/$tag.log 2>&1 || { tail -3 logs/$tag.log; return 1; }
  grep -E "SUMMARY|PASS|FAIL" logs/$tag.log | head -2
  DESIGN=$d MACRO_INST=$macro PERIOD_NS=20 RUN_DIR=$(rd $d) power/run_vcd_power.sh core sim/build_$tag/$tag.vcd > logs/vcd_power_$tag.log 2>&1 || { tail -3 logs/vcd_power_$tag.log; return 1; }
  grep -E "^Total" power/out_vcd_$tag/power_vcd.rpt | head -1
}
# E1: 200-bin functional window for the cores whose SDF window is 200 bins
for d in bmi_snn_top bmi_snn_topg bmi_snn_hw bmi_snn_min; do run $d ${d}_md0_f200 sim/vec_indy_20160630_01 200 0; done
# E9: the sequential SRAM core and the pruned core on 500 bins of the other two sessions (weights of indy_20160630_01)
for s in 20160622_01 20170131_02; do run bmi_snn_top bmi_snn_top_md0_x$s sim/vec_x630_on_$s 500 0; run bmi_snn_sp bmi_snn_sp_md0_x$s sim/vec_spx630_on_$s 500 0; done
# E5: SDF on 500 bins for the small hardwired cores (the 200-bin results are kept as *_sdf200)
for d in bmi_snn_min16 bmi_snn_min32 bmi_snn_sp bmi_snn_m12 bmi_snn_ming; do
  for k in sim/build_${d}_md0_sdf power/out_vcd_${d}_md0_sdf; do [ -d $k ] && [ ! -d ${k}200 ] && mv $k ${k}200; done
  rm -f sim/build_${d}_md0_sdf200/*.vcd
  case $d in bmi_snn_min32) vec=sim/vec_h32_indy_20160630_01;; bmi_snn_min16) vec=sim/vec_h16_indy_20160630_01;; bmi_snn_sp) vec=sim/vec_sp_indy_20160630_01;; bmi_snn_m12) vec=sim/vec_v12_indy_20160630_01;; *) vec=sim/vec_indy_20160630_01;; esac
  run $d ${d}_md0_sdf $vec 500 1
done
echo "REVIEW EXPERIMENTS E1/E9/E5 DONE $(date)"
