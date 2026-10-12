#!/usr/bin/env bash
# Round 10 (E10): every 10 min, measure the decap-free refill of every finished real-time run whose refilled netlist exists and whose
# decap-free report is still missing (cores: sim/measure_rt_nodecap.sh; SoC: sim/measure_rt_nodecap_soc.sh; IHP pruned core: the
# round-6 refill through sim/measure_rt_pdk.sh sta). Stops itself when nothing is pending and no simulation runs. Log: logs/rt10/nodecap_watch.log
cd "$(dirname "$0")/.."
while true; do
  pending=0
  for b in sim/build_rt_bmi_snn_*/toggles.tsv; do          # runs whose chain was interrupted after the simulation (see sim/rt_finish.sh)
    bd=$(dirname "$b"); tag=${bd#sim/build_}; [[ -f power/out_$tag/root_clock_correction.json ]] && continue
    grep -q "^PASS" "$bd/vvp.log" 2>/dev/null || continue
    pgrep -f "measure_rt.sh .*" > /dev/null && { busy=0; for p in $(pgrep -f "measure_rt.sh "); do [[ "$(tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null)" == *" $(echo $tag | sed -E 's/^rt_(bmi_snn_[a-z0-9]+)_5m.*/\1/') "* ]] && busy=1; done; [[ $busy -eq 1 ]] && continue; }
    for p in $(pgrep -f "vvp -n gls.vvp"); do [[ "$(readlink /proc/$p/cwd 2>/dev/null)" == "$PWD/$bd" ]] && continue 2; done
    d=$(echo "$tag" | sed -E 's/^rt_(bmi_snn_[a-z0-9]+)_5m.*/\1/'); rt=$(echo "$tag" | sed -E 's/^rt_(bmi_snn_[a-z0-9]+_5m[a-z_]*?)_(sdf|func)_md.*/\1/')
    echo "$(date +%H:%M:%S) finish $tag" >> logs/rt10/nodecap_watch.log; ./sim/rt_finish.sh "$d" "$tag" "$rt" >> logs/rt10/nodecap_watch.log 2>&1 || echo "FAILED finish $tag" >> logs/rt10/nodecap_watch.log
  done
  for j in power/out_rt_bmi_snn_*/root_clock_correction.json; do
    o=$(dirname "$j"); tag=${o#power/out_}; [[ $tag == *_nodecap || $tag == *_zero || $tag == *_cond || $tag == *_mcond ]] && continue
    d=$(echo "$tag" | sed -E 's/^rt_(bmi_snn_[a-z0-9]+)_5m.*/\1/'); rt=$(echo "$tag" | sed -E 's/^rt_(bmi_snn_[a-z0-9]+_5m[a-z_]*?)_(sdf|func)_md.*/\1/')
    [[ $tag == *_5m_lv_* || $tag == *_5m_nodecap_* ]] && continue
    if [[ ($d == bmi_snn_top || $d == bmi_snn_topg) && ! -f "$o/macro_state_correction.json" ]]; then echo "$(date +%H:%M:%S) post $tag" >> logs/rt10/nodecap_watch.log; ./sim/rt_post.sh "$d" "$tag" "$rt" >> logs/rt10/nodecap_watch.log 2>&1 || echo "FAILED post $tag" >> logs/rt10/nodecap_watch.log; fi
    [[ -f synthesis/$d/runs/${rt}_nodecap/final/nl/$d.nl.v ]] || { pending=1; continue; }
    [[ -f "${o}_nodecap/root_clock_correction.json" ]] && continue
    echo "$(date +%H:%M:%S) nodecap $tag" >> logs/rt10/nodecap_watch.log; ./sim/measure_rt_nodecap.sh "$d" "$tag" "$rt" >> logs/rt10/nodecap_watch.log 2>&1 || echo "FAILED $tag" >> logs/rt10/nodecap_watch.log
  done
  for v in _5m_tuned_rt100 _5m_o2_rt100; do
    [[ -f power/out_riscv_rt$v/root_clock_correction.json && ! -f power/out_riscv_rt$v/macro_state_correction.json ]] && { echo "$(date +%H:%M:%S) post SoC $v" >> logs/rt10/nodecap_watch.log; ./sim/rt_post_soc.sh $v >> logs/rt10/nodecap_watch.log 2>&1 || echo "FAILED post soc $v" >> logs/rt10/nodecap_watch.log; }
    [[ -f power/out_riscv_rt$v/root_clock_correction.json && ! -f power/out_riscv_rt${v}_nodecap/root_clock_correction.json ]] && { echo "$(date +%H:%M:%S) nodecap SoC $v" >> logs/rt10/nodecap_watch.log; ./sim/measure_rt_nodecap_soc.sh $v >> logs/rt10/nodecap_watch.log 2>&1 || echo "FAILED soc $v" >> logs/rt10/nodecap_watch.log; }
    [[ -f power/out_riscv_rt$v/root_clock_correction.json ]] || pending=1
  done
  if [[ -f power/out_rt_pdk_ihp_sp_sdf_w5000/root_clock_correction.json && ! -f power/out_rt_pdk_ihp_sp_nodecap_sdf_w5000/root_clock_correction.json ]]; then
    echo "$(date +%H:%M:%S) nodecap IHP sp (round-6 refill)" >> logs/rt10/nodecap_watch.log; RUN_NICK=bmi_snn_sp_5m_nodecap TAG_SFX=_nodecap ./sim/measure_rt_pdk.sh ihp sp 5000 sta >> logs/rt10/nodecap_watch.log 2>&1 || echo "FAILED ihp nodecap" >> logs/rt10/nodecap_watch.log
  fi
  [[ -f power/out_rt_pdk_ihp_sp_sdf_w5000/root_clock_correction.json ]] || pending=1
  running=$(ps -eo args | grep -cE "^bash ./sim/(measure_rt|measure_rt_pdk|run_riscv_rt).sh")
  [[ $pending -eq 0 && $running -eq 0 ]] && { echo "$(date +%H:%M:%S) nothing pending, exiting" >> logs/rt10/nodecap_watch.log; exit 0; }
  sleep 600
done
