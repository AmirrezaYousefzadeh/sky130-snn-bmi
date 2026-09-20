#!/usr/bin/env bash
# Round 5 (E4/E11): per-pin power of every finished E4 window of the SRAM cores (func_full / func_w20000 / sdf_w2000 of top and topg)
# with the vdd-only SRAM22 liberty as primary (power/out_vcd_<tag>/, read first by sw/collect_designs5.py) and the as-generated
# liberty as sensitivity (power/out_vcd_<tag>_asgen/); the measure_full.sh runs started before 20:15 wrote the as-generated result
# to power/out_<tag>/. Idempotent: existing reports are kept.  Usage: sim/sram_full_windows_power.sh
set -uo pipefail; cd "$(dirname "$0")/.."
for D in bmi_snn_top bmi_snn_topg; do
  tags=""; for b in sim/build_${D}_5m_func_* sim/build_${D}_5m_sdf_*; do [[ -f "$b/toggles.tsv" && -f "$b/vvp.log" ]] && grep -q "^SUMMARY" "$b/vvp.log" && tags="$tags $(basename "$b" | sed "s/^build_${D}_5m_//")"; done
  for t in $tags; do
    if [[ -f "power/out_vcd_${D}_5m_$t/power_vcd.rpt" && -f "power/out_vcd_${D}_5m_${t}_asgen/power_vcd.rpt" ]]; then continue; fi
    ./sim/sram_windows_power.sh "$D" $t 2>&1 | grep -v "^====" | cut -c1-140
  done
done
echo "==== SRAM full windows power done ($(date +%H:%M:%S))"
