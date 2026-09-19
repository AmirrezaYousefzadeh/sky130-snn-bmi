#!/usr/bin/env bash
# Round 5 (E5): run sim/measure_pdk5.sh for a list of kit:core[:kinds] items, N at a time. Usage: pdk5_queue.sh <N> item...
N="$1"; shift; cd "$(dirname "$0")/.."
for it in "$@"; do
  while [[ $(pgrep -fc "measure_pdk5.s[h]") -ge $N ]]; do sleep 60; done
  IFS=: read -r kit core kinds <<< "$it"; kinds="${kinds:-func volt}"
  ( for k in $kinds; do ./sim/measure_pdk5.sh "$kit" "$core" "$k"; done ) > "logs/pdk5_${kit}_${core}.log" 2>&1 &
  sleep 5
done
wait
