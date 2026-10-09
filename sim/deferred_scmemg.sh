#!/usr/bin/env bash
# Round 10: retry the 30 % hardening of bmi_snn_scmemg once the machine has memory to spare, then restart the hardening watcher
cd "$(dirname "$0")/.."
until [ "$(free -g | awk 'NR==2{print $7}')" -ge 32 ]; do sleep 300; done
echo "$(date +%H:%M:%S) launching scmemg 30 % retry (available $(free -g | awk 'NR==2{print $7}') GB)" >> logs/rt10/harden_watch.log
WD_VIOL3=200000 WD_VIOL8=20000 TAG_SUFFIX=r2 nohup ./synthesis/harden_policy2.sh bmi_snn_scmemg 200 "30" > logs/harden_bmi_snn_scmemg_retry2.log 2>&1 &
sleep 5
W=$(ps -eo pid,args | awk '$2=="bash" && $3=="./sim/harden_watch10.sh" {print $1}'); [ -n "$W" ] && kill $W; sleep 1; nohup ./sim/harden_watch10.sh > /dev/null 2>&1 &
