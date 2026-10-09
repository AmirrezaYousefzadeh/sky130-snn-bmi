#!/usr/bin/env bash
# Round 10: re-run the root-clock correction (power/root_clock_correction.py) on every finished real-time run of this round with the
# current version of the script (root registers scaled by the duty directly), in place. Prints the change of the corrected total.
cd "$(dirname "$0")/.."; ORFS=/media/pdk/OpenROAD-flow-scripts/flow; SKY=$HOME/workspace/skywater
for j in power/out_rt_*/root_clock_correction.json power/out_riscv_rt*/root_clock_correction.json power/out_rt_fe_v3_gls_5m/root_clock_correction.json; do
  o=$(dirname "$j"); tag=${o#power/out_}; [[ $tag == *_zero ]] && continue
  base=${tag%_cond}; base=${base%_mcond}; zero="power/out_${base}_zero"; port=clk; nl=""; pre=""
  if [[ $tag == rt_fe_v3_gls_5m ]]; then nl=synthesis/bmi_fe/runs/bmi_fe_5m/final/nl/bmi_fe.nl.v; port=clk5
  elif [[ $tag == riscv_rt* ]]; then run=sky130_vex2_soc_5m; [[ $base == *_nodecap ]] && run=${run}_nodecap; nl=$SKY/synthesis/sky130_vex2_soc/runs/$run/final/nl/sky130_vex2_soc.nl.v
  elif [[ $tag == rt_pdk_* ]]; then
    kit=$(echo $tag | sed -E 's/^rt_pdk_([a-z0-9]+)_sp.*/\1/'); rn=bmi_snn_sp_5m; [[ $base == *_sp_nodecap_* ]] && rn=bmi_snn_sp_5m_nodecap
    case $kit in gf180) nl=synthesis/pdk_gf180/bmi_snn_sp/runs/$rn/final/nl/bmi_snn_sp.nl.v ;; nangate45) nl=$ORFS/results/nangate45/$rn/base/6_final.v ;; ihp) nl=$ORFS/results/ihp-sg13g2/$rn/base/6_final.v ;;
      asap7) nl=$ORFS/results/asap7/$rn/base/6_final.v ;; asap7sram) nl=$ORFS/results/asap7/${rn}_sram/base/6_final.v ;; esac
  else
    d=$(echo $tag | sed -E 's/^rt_(bmi_snn_[a-z0-9]+)_5m.*/\1/'); run=$(echo $tag | sed -E 's/^rt_(bmi_snn_[a-z0-9]+_5m[a-z_]*?)_(sdf|func)_md.*/\1/'); [[ $base == *_nodecap ]] && run=${run}_nodecap
    nl=synthesis/$d/runs/$run/final/nl/$d.nl.v
  fi
  [[ -f "$nl" && -f "$zero/power_vcd_by_instance.rpt" ]] || { echo "SKIP $tag (netlist $nl, zero $zero)"; continue; }
  duty=$(python3 -c "import json; print(json.load(open('$j'))['duty'])"); before=$(python3 -c "import json; j=json.load(open('$j')); c=j.get('corrected_report') or j['corrected']['Total']; print('%.6f' % (c['total']*1e6))")
  python3 power/root_clock_correction.py "$nl" $port "$duty" "$o/power_vcd_by_instance.rpt" "$zero/power_vcd_by_instance.rpt" -o "$j" > /dev/null || { echo "FAILED $tag"; continue; }
  after=$(python3 -c "import json; j=json.load(open('$j')); c=j.get('corrected_report') or j['corrected']['Total']; print('%.6f' % (c['total']*1e6))")
  printf "%-70s %12s -> %12s uW\n" "$tag" "$before" "$after"
done
