#!/usr/bin/env bash
# E4 windows of bmi_snn_topg in parallel (the sequential pipeline would need days for the SRAM core's full block): waits for the
# 200-bin annotated window of measure_design, then runs full block B, 20k bins of A and C, 2,000 annotated bins per session.
cd "$(dirname "$0")/.."; export RUN_TAG=bmi_snn_topg_5m CLK_NS=200
while [[ ! -f power/out_vcd_bmi_snn_topg_5m_md0_sdf/power_vcd.rpt ]]; do sleep 120; done
./sim/measure_full.sh bmi_snn_topg indy_20160630_01 func full > logs/topg_full_func_full_B.log 2>&1 &
for s in indy_20160622_01 indy_20170131_02; do ./sim/measure_full.sh bmi_snn_topg $s func 20000 > logs/topg_full_func_w20000_$s.log 2>&1 & done
for s in indy_20160630_01 indy_20160622_01 indy_20170131_02; do ./sim/measure_full.sh bmi_snn_topg $s sdf 2000 > logs/topg_full_sdf_w2000_$s.log 2>&1 & done
wait; echo "==== topg windows done ($(date +%H:%M))"
