#!/usr/bin/env bash
# E2: seed variance of every reported configuration (H64 dense, 50 / 25 / 12.5 % synapses, H32, H16), seeds 1-4 on top of the
# released seed-0 models; three sessions; the standard recipe (1500 steps, dropout 0.1, lr 2.0, theta 256, leak 4/4).
# Four training jobs run concurrently on the GPU. Output: results/models/<session>_H<H>_th256_k44<tag>_s<seed>/
cd "$(dirname "$0")/.."
SESS="indy_20160622_01 indy_20160630_01 indy_20170131_02"
jobs_list=()
for seed in 1 2 3 4; do for s in $SESS; do
  jobs_list+=("--session $s --H 64 --seed $seed --tag _drop_s$seed")
  jobs_list+=("--session $s --H 32 --seed $seed --tag _drop_s$seed")
  jobs_list+=("--session $s --H 16 --seed $seed --tag _drop_s$seed")
  for d in 0.5 0.25 0.125; do jobs_list+=("--session $s --H 64 --seed $seed --prune $d --prune_start 0.2 --prune_end 0.6 --tag _drop_p${d}_s$seed"); done
done; done
echo "${#jobs_list[@]} training runs"
run_one() { local args="$1"; local name=$(echo "$args" | sed 's/--session //; s/ --H /_H/; s/ --seed [0-9]//; s/ --prune \([0-9.]*\) --prune_start 0.2 --prune_end 0.6//; s/ --tag //'); 
  .venv/bin/python sw/train_snn.py $args --theta 256 --epochs 1500 --eval_every 100 --drop 0.1 --lr 2.0 > logs/seed_$name.log 2>&1; }
n=0
for a in "${jobs_list[@]}"; do run_one "$a" & n=$((n+1)); if [ $((n % 4)) -eq 0 ]; then wait; fi; done; wait
echo "SEED SWEEP DONE $(date)"
