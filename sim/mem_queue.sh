#!/usr/bin/env bash
# Round 10: memory-aware job queue. Runs the lines of <jobfile> one after another; a job is started only when `free` reports at
# least <min_avail_GB> available, and the file is re-read after every job so that lines appended later are picked up.
# Usage: mem_queue.sh <min_avail_GB> <jobfile>      Log: logs/rt10/mem_queue.log
cd "$(dirname "$0")/.."; MIN="$1"; JF="$2"; L=logs/rt10/mem_queue.log; n=0
while true; do
  total=$(grep -cvE '^\s*(#|$)' "$JF"); [[ $n -ge $total ]] && { sleep 300; [[ $(grep -cvE '^\s*(#|$)' "$JF") -gt $n ]] && continue; [[ -f "$JF.close" ]] && { echo "$(date +%H:%M:%S) queue closed after $n jobs" >> $L; exit 0; }; continue; }
  job=$(grep -vE '^\s*(#|$)' "$JF" | sed -n "$((n+1))p")
  until [[ "$(free -g | awk 'NR==2{print $7}')" -ge "$MIN" ]]; do sleep 120; done
  echo "$(date +%H:%M:%S) start (available $(free -g | awk 'NR==2{print $7}') GB): $job" >> $L
  bash -c "$job" > "logs/rt10/mq_$(echo "$job" | tr ' /=' '___' | cut -c1-120).log" 2>&1; echo "$(date +%H:%M:%S) end($?): $job" >> $L
  n=$((n+1)); sleep 60
done
