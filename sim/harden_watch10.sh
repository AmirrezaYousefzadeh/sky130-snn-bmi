#!/usr/bin/env bash
# Round 10: when a new hardening is accepted (runs/<design>_5m link appears), launch its real-time runs and its decap-free refill.
# Designs and runs: hwg sdf 5000 | scmemg, lmem2g: sdf 50 + func 5000 | g16: sdf 5000 + func 5000. Log: logs/rt10/harden_watch.log
cd "$(dirname "$0")/.."; L=logs/rt10/harden_watch.log
declare -A JOBS=([bmi_snn_hwg]="sdf 5000" [bmi_snn_scmemg]="sdf 50|func 5000" [bmi_snn_lmem2g]="sdf 50|func 5000" [bmi_snn_g16]="sdf 5000|func 5000")
declare -A DONE
while true; do
  left=0
  for d in "${!JOBS[@]}"; do
    [[ -n "${DONE[$d]:-}" ]] && continue
    [[ -f logs/rt10/launched_$d ]] && { DONE[$d]=1; continue; }        # launched by an earlier instance of this watcher (marker file)
    if [[ -L synthesis/$d/runs/${d}_5m && -f synthesis/$d/runs/${d}_5m/final/nl/$d.nl.v ]]; then
      echo "$(date +%H:%M:%S) $d accepted ($(readlink synthesis/$d/runs/${d}_5m)): launching real-time runs and the refill" >> $L
      touch logs/rt10/launched_$d
      IFS='|' read -ra runs <<< "${JOBS[$d]}"
      for r in "${runs[@]}"; do set -- $r; nohup ./sim/measure_rt_g.sh $d $1 $2 > logs/rt10/${d}_$1_$2.log 2>&1 & sleep 2; done
      if [[ $d == bmi_snn_scmemg || $d == bmi_snn_lmem2g ]]; then echo "./synthesis/refill_nodecap.sh synthesis/$d ${d}_5m" >> logs/rt10/jobs_mem_queue2.txt
      else echo "./synthesis/refill_nodecap.sh synthesis/$d ${d}_5m" > logs/rt10/jobs_refill_$d.txt; nohup ./sim/rt_queue.sh 1 logs/rt10/jobs_refill_$d.txt > /dev/null 2>&1 & fi
      DONE[$d]=1
    else
      # a design whose policy has given up (no process, no accepted link) is reported once
      if ! pgrep -f "harden_policy2.sh $d " > /dev/null; then echo "$(date +%H:%M:%S) $d: policy not running and no accepted netlist" >> $L; DONE[$d]=gaveup; else left=1; fi
    fi
  done
  [[ $left -eq 0 ]] && { echo "$(date +%H:%M:%S) all hardenings handled, exiting" >> $L; exit 0; }
  sleep 120
done
