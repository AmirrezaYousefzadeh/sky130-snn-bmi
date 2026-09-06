#!/usr/bin/env bash
# Voltage-scaling study on the existing SDF waveforms: designs x corners (sequential, one STA at a time).
cd "$(dirname "$0")/.."
DESIGNS="${DESIGNS:-bmi_snn_min16 bmi_snn_min32 bmi_snn_min bmi_snn_hw}"
CORNERS="${CORNERS:-ss_100C_1v40 ss_n40C_1v40 ss_n40C_1v28 tt_100C_1v80}"
for d in $DESIGNS; do
  case $d in bmi_snn_min) RD=synthesis/bmi_snn_min_lo/runs/bmi_snn_min_lo;; bmi_snn_hw) RD=synthesis/bmi_snn_hw_lo/runs/bmi_snn_hw_lo;; *) RD=synthesis/$d/runs/$d;; esac
  for c in $CORNERS; do for k in md0_sdf idle_sdf; do
    [ -f power/out_vcd_${d}_${k}_$c/power_vcd.rpt ] && continue
    echo "== $d $k $c $(date +%H:%M)"; RUN_DIR=$PWD/$RD power/run_corner_power.sh $d ${d}_$k $c || echo "FAILED $d $k $c"
  done; done
done; echo "CORNER SET DONE $(date)"
