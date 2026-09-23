#!/usr/bin/env bash
# Round 6: every 10 min, re-annotate (OpenSTA only) the kit runs whose reports were made with CLK_STOP_ICG=1, until every output is clean
# and no kit measurement is running. Usage: sim/reannotate_watch6.sh (background); log to stdout.
cd "$(dirname "$0")/.."
while true; do
  todo=0
  for d in power/out_vcd_pdk5_*/sta.log; do grep -q "CLK_STOP_ICG:" "$d" 2>/dev/null && todo=$((todo+1)); done
  running=$(ps -eo args | grep -c "^bash ./sim/measure_pdk5.sh .* \(func\|sdf\|volt\|w5000\|all\)$")
  echo "$(date +%H:%M:%S): $todo reports still with the clock-gate stop, $running kit measurements running"
  if [[ $todo -eq 0 && $running -eq 0 ]]; then echo "==== all kit reports clean ($(date +%H:%M:%S))"; break; fi
  for pair in $(ls -d power/out_vcd_pdk5_*/ | sed -E 's#power/out_vcd_pdk5_([a-z0-9]+)_([a-z0-9]+)_.*#\1:\2#' | sort -u); do
    kit=${pair%%:*}; core=${pair##*:}; [[ $core == nodecap || $core == sp_nodecap ]] && continue
    dirty=0; for d in power/out_vcd_pdk5_${kit}_${core}_*/sta.log; do grep -q "CLK_STOP_ICG:" "$d" 2>/dev/null && dirty=1; done
    [[ $dirty -eq 1 ]] && ./sim/measure_pdk5.sh "$kit" "$core" sta 2>&1 | grep -E "^====|Total" | cut -c1-150
  done
  sleep 600
done
