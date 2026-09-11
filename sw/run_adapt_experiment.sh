#!/usr/bin/env bash
# E11 (software part): can a core with hardwired W1 be recalibrated to another session by retraining only the bias row and
# the read-out (W2, g, b)? W1 from the dense H=64 model of session A, adapted on session B; compared with full training on B.
cd "$(dirname "$0")/.."
S=(indy_20160622_01 indy_20160630_01 indy_20170131_02)
for a in "${S[@]}"; do for b in "${S[@]}"; do [ "$a" = "$b" ] && continue
  .venv/bin/python sw/train_snn.py --session $b --H 64 --theta 256 --epochs 1500 --eval_every 100 --drop 0.1 --lr 2.0 \
    --init_from results/models/${a}_H64_th256_k44_drop --train_only bias_w2 --tag _adaptW1from_${a#indy_} > logs/adapt_${a#indy_}_to_${b#indy_}.log 2>&1 &
done; done; wait
# also: W1 from A applied to B with NO adaptation (integer reference, no training) is evaluated by sw/eval_transfer.py
echo "ADAPT DONE $(date)"
