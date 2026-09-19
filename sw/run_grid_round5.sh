#!/usr/bin/env bash
# E2 (round 5): energy-accuracy grid of the hardwired family, new configurations only.
# H=128 dense / 25 % / 12.5 %, H=32 50 % / 25 %, H=16 50 %; seeds 0-4; three sessions; standard recipe (1500 steps, dropout 0.1,
# lr 2.0, theta 256, leak 4/4, gradual magnitude pruning between 20 % and 60 % of the steps). Four jobs concurrently on the GPU.
# Output: results/models/<session>_H<H>_th256_k44_drop[_p<d>][_s<seed>]/ (seed 0 has no _s suffix, as in the released models).
cd "$(dirname "$0")/.."
SESS="indy_20160622_01 indy_20160630_01 indy_20170131_02"
jobs_list=()
for seed in 0 1 2 3 4; do for s in $SESS; do
  st=""; [ $seed -gt 0 ] && st="_s$seed"; sd=""; [ $seed -gt 0 ] && sd="--seed $seed"
  jobs_list+=("--session $s --H 128 $sd --tag _drop$st")
  for d in 0.25 0.125; do jobs_list+=("--session $s --H 128 $sd --prune $d --prune_start 0.2 --prune_end 0.6 --tag _drop_p${d}$st"); done
  for d in 0.5 0.25; do jobs_list+=("--session $s --H 32 $sd --prune $d --prune_start 0.2 --prune_end 0.6 --tag _drop_p${d}$st"); done
  jobs_list+=("--session $s --H 16 $sd --prune 0.5 --prune_start 0.2 --prune_end 0.6 --tag _drop_p0.5$st")
done; done
echo "${#jobs_list[@]} training runs ($(date))"
run_one() { local args="$1"
  local sess=$(echo "$args" | sed 's/--session \([^ ]*\).*/\1/'); local H=$(echo "$args" | sed 's/.*--H \([0-9]*\).*/\1/'); local tag=$(echo "$args" | sed 's/.*--tag \([^ ]*\).*/\1/')
  local out="results/models/${sess}_H${H}_th256_k44${tag}"
  if [ -f "$out/train.json" ]; then echo "skip $out"; return; fi
  .venv/bin/python sw/train_snn.py $args --theta 256 --epochs 1500 --eval_every 100 --drop 0.1 --lr 2.0 > "logs/grid5_${sess}_H${H}${tag}.log" 2>&1 || echo "FAILED: $args"; }
n=0
for a in "${jobs_list[@]}"; do run_one "$a" & n=$((n+1)); if [ $((n % 4)) -eq 0 ]; then wait; fi; done; wait
echo "GRID5 DONE $(date)"
