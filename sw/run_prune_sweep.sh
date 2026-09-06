#!/usr/bin/env bash
# Gradual magnitude pruning sweep of the H=64 recipe (drop 0.1, 1500 steps, lr 2.0): sessions x W1 densities.
# Usage: run_prune_sweep.sh [sessions...]   (default: all three)
cd "$(dirname "$0")/.."
SESS="${@:-indy_20160622_01 indy_20160630_01 indy_20170131_02}"
for dens in 0.5 0.25 0.125; do
  ( for s in $SESS; do
      .venv/bin/python sw/train_snn.py --session $s --H 64 --theta 256 --epochs 1500 --eval_every 100 --drop 0.1 --lr 2.0 \
        --prune $dens --prune_start 0.2 --prune_end 0.6 --tag _drop_p$dens > logs/train_${s}_H64_p$dens.log 2>&1
    done ) &
done
wait; echo "PRUNE SWEEP DONE $(date)"
