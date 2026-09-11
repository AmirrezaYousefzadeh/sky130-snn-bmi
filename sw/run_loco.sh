#!/usr/bin/env bash
# E6: the Loco sessions used by NeuroBench (192 channels): prepare, train the H=64 recipe (seed 0), evaluate with the integer model.
cd "$(dirname "$0")/.."
until [ -f data/prepared/loco_20170215_02.npz ] && [ -f data/prepared/loco_20170301_05.npz ]; do sleep 30; done
[ -f data/prepared/loco_20170210_03.npz ] || .venv/bin/python sw/prepare_data.py data/loco_20170210_03.mat > logs/prepare_loco3.log 2>&1
for s in loco_20170210_03 loco_20170215_02 loco_20170301_05; do
  .venv/bin/python sw/train_snn.py --session $s --H 64 --theta 256 --epochs 1500 --eval_every 100 --drop 0.1 --lr 2.0 --tag _drop > logs/train_${s}_H64_drop.log 2>&1 &
done; wait
.venv/bin/python sw/eval_int.py results/models/loco_*_H64_th256_k44_drop > logs/eval_loco.log 2>&1
echo "LOCO DONE $(date)"
