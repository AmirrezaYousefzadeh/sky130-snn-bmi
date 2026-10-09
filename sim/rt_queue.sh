#!/usr/bin/env bash
# Round 10: run the command lines of a job file, at most N at a time (one log per job in logs/rt10/). Usage: rt_queue.sh <N> <jobfile>
cd "$(dirname "$0")/.."; N="$1"; JOBS="$2"; mkdir -p logs/rt10
grep -vE '^\s*(#|$)' "$JOBS" | xargs -P "$N" -I{} bash -c 'l="logs/rt10/q_$(echo "{}" | tr " /=" "___" | cut -c1-120).log"; echo "$(date +%H:%M:%S) start: {}" >> logs/rt10/queue.log; {} > "$l" 2>&1; echo "$(date +%H:%M:%S) end($?): {}" >> logs/rt10/queue.log'
echo "queue $JOBS done ($(date +%H:%M:%S))"
