#!/usr/bin/env bash
# Round 6 (E4d): four more grid points of the hardwired family: H=48 dense / 50 % / 25 %, H=32 12.5 %; seeds 0-4; three sessions;
# the round-5 recipe (1500 steps, dropout 0.1, lr 2.0, theta 256, leak 4/4, gradual magnitude pruning 20-60 % of the steps).
# Four jobs concurrently on the GPU (each ~400 MB, ~2 min). Output: results/models/<session>_H<H>_th256_k44_drop[_p<d>][_s<seed>]/
cd "$(dirname "$0")/.."
SESS="indy_20160622_01 indy_20160630_01 indy_20170131_02"
jobs_list=()
for seed in 0 1 2 3 4; do for s in $SESS; do
  st=""; [ $seed -gt 0 ] && st="_s$seed"; sd=""; [ $seed -gt 0 ] && sd="--seed $seed"
  jobs_list+=("--session $s --H 48 $sd --tag _drop$st")
  for d in 0.5 0.25; do jobs_list+=("--session $s --H 48 $sd --prune $d --prune_start 0.2 --prune_end 0.6 --tag _drop_p${d}$st"); done
  jobs_list+=("--session $s --H 32 $sd --prune 0.125 --prune_start 0.2 --prune_end 0.6 --tag _drop_p0.125$st")
done; done
echo "${#jobs_list[@]} training runs ($(date))"
run_one() { local args="$1"
  local sess=$(echo "$args" | sed 's/--session \([^ ]*\).*/\1/'); local H=$(echo "$args" | sed 's/.*--H \([0-9]*\).*/\1/'); local tag=$(echo "$args" | sed 's/.*--tag \([^ ]*\).*/\1/')
  local out="results/models/${sess}_H${H}_th256_k44${tag}"
  if [ -f "$out/train.json" ]; then echo "skip $out"; return; fi
  .venv/bin/python sw/train_snn.py $args --theta 256 --epochs 1500 --eval_every 100 --drop 0.1 --lr 2.0 > "logs/grid6_${sess}_H${H}${tag}.log" 2>&1 || echo "FAILED: $args"; }
# the GPU is shared with another user's job (6.3 of 7.6 GB): two at a time, and up to four passes to redo runs that hit CUDA OOM
CONC="${CONC:-2}"
for pass in 1 2 3 4; do
  n=0; echo "== pass $pass ($(date +%H:%M))"
  for a in "${jobs_list[@]}"; do run_one "$a" & n=$((n+1)); if [ $((n % CONC)) -eq 0 ]; then wait; fi; done; wait
  missing=0; for a in "${jobs_list[@]}"; do sess=$(echo "$a" | sed 's/--session \([^ ]*\).*/\1/'); H=$(echo "$a" | sed 's/.*--H \([0-9]*\).*/\1/'); tag=$(echo "$a" | sed 's/.*--tag \([^ ]*\).*/\1/'); [ -f "results/models/${sess}_H${H}_th256_k44${tag}/train.json" ] || missing=$((missing+1)); done
  echo "pass $pass: $missing runs missing"; [ $missing -eq 0 ] && break; sleep 60
done
echo "GRID6 DONE $(date)"
