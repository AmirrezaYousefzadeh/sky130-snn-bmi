#!/usr/bin/env bash
# Round 5 (E1/E11): per-pin power of the SRAM cores' 500/200-bin windows through the streamed toggle path (a 5-16 GB OpenSTA VCD
# read per window is not affordable next to the flows), with the vdd-only SRAM22 liberty as the primary figure
# (power/out_vcd_<tag>/) and the as-generated liberty (both supply rails summed by OpenSTA) as sensitivity (power/out_vcd_<tag>_asgen/).
# Usage: sim/sram_windows_power.sh <bmi_snn_top|bmi_snn_topg> [tags...]
set -uo pipefail; cd "$(dirname "$0")/.."; D="$1"; shift; RT="${D}_5m"; RUN="$PWD/synthesis/$D/runs/$RT"
PWRLIB="$PWD/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib"; ASGEN="$PWD/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80.lib"
TAGS="${@:-md0_full md1_full idle_full md0_sdf md1_sdf idle_sdf}"
for t in $TAGS; do
  tag="${RT}_$t"; vcd="sim/build_$tag/$tag.vcd"; tsv="sim/build_$tag/toggles.tsv"
  [[ -f "$vcd" || -f "$tsv" ]] || { echo "$tag: no waveform"; continue; }
  [[ -f "$tsv" ]] || { echo "==== $tag: toggles ($(date +%H:%M:%S))"; ./tools/vcd_toggles -o "$tsv" "$vcd" 2> "sim/build_$tag/toggles.log" || { echo "toggles failed"; continue; }; }
  if [[ -f "power/out_vcd_$tag/power_vcd.rpt" && ! -d "power/out_vcd_${tag}_asgen" ]]; then mv "power/out_vcd_$tag" "power/out_vcd_${tag}_asgen"; fi   # keep the earlier read_vcd result (as-generated liberty)
  DESIGN=$D MACRO_INST=u_wmem PERIOD_NS=200 RUN_DIR="$RUN" LIB_SRAM="$PWRLIB" ./power/run_toggles_power.sh core "$tsv" "power/out_vcd_$tag" > "logs/power_$tag.log" 2>&1 || { tail -3 "logs/power_$tag.log"; continue; }
  [[ -f "power/out_vcd_${tag}_asgen/power_vcd.rpt" ]] || DESIGN=$D MACRO_INST=u_wmem PERIOD_NS=200 RUN_DIR="$RUN" LIB_SRAM="$ASGEN" ./power/run_toggles_power.sh core "$tsv" "power/out_vcd_${tag}_asgen" > "logs/power_${tag}_asgen.log" 2>&1
  echo "$tag: pwr $(grep -h '^Total' power/out_vcd_$tag/power_vcd.rpt | awk '{print $5}') W (macro $(grep -h '^Total' power/out_vcd_$tag/power_vcd_u_wmem.rpt 2>/dev/null | awk '{print $5}')) | asgen $(grep -h '^Total' power/out_vcd_${tag}_asgen/power_vcd.rpt 2>/dev/null | awk '{print $5}')"
done
echo "==== $D windows power done ($(date +%H:%M:%S))"
