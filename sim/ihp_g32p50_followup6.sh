#!/usr/bin/env bash
# Round 6: when the IHP g32p50 hardening ends, measure it (decode/idle/corners, 5,000-bin window, re-annotation), refresh all collectors,
# tables and figures, and log. Usage: nohup sim/ihp_g32p50_followup6.sh <run_orfs5 pid> > logs/pdk6_ihp_followup.log 2>&1 &
cd "$(dirname "$0")/.."; PID="$1"
while kill -0 "$PID" 2>/dev/null; do sleep 300; done
echo "IHP g32p50 policy finished ($(date +%H:%M:%S))"; grep "ihp-sg13g2 rvt bmi_snn_g32p50" logs/orfs5_policy.log | tail -n 3
if grep -q "ihp-sg13g2 rvt bmi_snn_g32p50 ACCEPTED" logs/orfs5_policy.log; then
  ./sim/measure_pdk5.sh ihp g32p50 all > logs/pdk5_ihp_g32p50.log 2>&1
  ./sim/measure_pdk5.sh ihp g32p50 w5000 >> logs/pdk5_ihp_g32p50.log 2>&1
  STA_MIN_AGE=0 ./sim/measure_pdk5.sh ihp g32p50 sta >> logs/pdk5_ihp_g32p50.log 2>&1
  grep -E "^====|Total" logs/pdk5_ihp_g32p50.log | cut -c1-140 | tail -n 12
  ./sw/refresh_round6.sh > logs/refresh_round6_ihp.log 2>&1; cat logs/refresh_round6_ihp.log
  grep -E "IHP SG13G2 & GcHalf" paper/pdks_table.tex | cut -c1-200
  echo "==== IHP g32p50 follow-up done ($(date +%H:%M:%S))"
else echo "==== IHP g32p50 not accepted ($(date +%H:%M:%S))"; fi
