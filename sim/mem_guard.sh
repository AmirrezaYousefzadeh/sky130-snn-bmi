#!/usr/bin/env bash
# Round 10: memory guard. When MemAvailable drops below LOW (kB) the largest running gate-level simulation (vvp) is paused with SIGSTOP;
# when it rises above HIGH the most recently paused one is resumed. Protects the OpenLane hardenings (hours) from the OOM killer at the
# cost of delaying simulations. Log: logs/rt10/mem_guard.log. Usage: nohup sim/mem_guard.sh &
LOW=${LOW:-3500000}; HIGH=${HIGH:-9000000}; STOPPED=()
cd "$(dirname "$0")/.."
while true; do
  avail=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
  if [[ $avail -lt $LOW ]]; then
    p=$(ps -eo pid,rss,stat,args --sort=-rss | awk '$4 ~ /ld-linux|vvp/ && $3 !~ /T/ {print $1; exit}')
    if [[ -n "$p" ]]; then kill -STOP $p && STOPPED+=($p) && echo "$(date +%H:%M:%S) avail ${avail}kB: paused vvp $p ($(readlink /proc/$p/cwd 2>/dev/null | sed 's#.*/##'))" >> logs/rt10/mem_guard.log; fi
  elif [[ $avail -gt $HIGH && ${#STOPPED[@]} -gt 0 ]]; then
    p=${STOPPED[-1]}; unset 'STOPPED[-1]'
    kill -CONT $p 2>/dev/null && echo "$(date +%H:%M:%S) avail ${avail}kB: resumed vvp $p" >> logs/rt10/mem_guard.log
  fi
  sleep 15
done
