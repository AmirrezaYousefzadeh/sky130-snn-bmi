#!/usr/bin/env bash
# E4 (round 5): test vectors of the FULL test block of each session for every core width / model family.
#   vecfull_indy_<s>      H=64 dense, 20/24-bit state (bmi_snn_top, bmi_snn_hw, bmi_snn_lmem2, bmi_snn_scmem)
#   vecfull_v16_indy_<s>  H=64 dense, 16/16               (bmi_snn_min, bmi_snn_ming)
#   vecfull_v12_indy_<s>  H=64 dense, 12/14               (bmi_snn_m12, bmi_snn_lmin2)
#   vecfull_sp_indy_<s>   H=64 25 % synapses, 12/14      (bmi_snn_sp)
#   vecfull_h32_indy_<s>  H=32 dense, 16/16               (bmi_snn_min32)
#   vecfull_h16_indy_<s>  H=16 dense, 16/16               (bmi_snn_min16)
cd "$(dirname "$0")/.."
nb() { .venv/bin/python -c "import numpy as np; d=np.load('data/prepared/$1.npz'); print(len(d['ind_test']))"; }
for s in indy_20160622_01 indy_20160630_01 indy_20170131_02; do
  N=$(nb $s); echo "$s: $N test bins"
  M=results/models/${s}_H64_th256_k44_drop
  .venv/bin/python sw/export_vectors.py $M --n_bins $N --vbits 20 --obits 24 --out sim/vecfull_$s > logs/vecfull_$s.log 2>&1 &
  .venv/bin/python sw/export_vectors.py $M --n_bins $N --vbits 16 --obits 16 --out sim/vecfull_v16_$s > logs/vecfull_v16_$s.log 2>&1 &
  .venv/bin/python sw/export_vectors.py $M --n_bins $N --vbits 12 --obits 14 --out sim/vecfull_v12_$s > logs/vecfull_v12_$s.log 2>&1 &
  .venv/bin/python sw/export_vectors.py results/models/${s}_H64_th256_k44_drop_p0.25 --n_bins $N --vbits 12 --obits 14 --out sim/vecfull_sp_$s > logs/vecfull_sp_$s.log 2>&1 &
  .venv/bin/python sw/export_vectors.py results/models/${s}_H32_th256_k44_drop --n_bins $N --vbits 16 --obits 16 --out sim/vecfull_h32_$s > logs/vecfull_h32_$s.log 2>&1 &
  .venv/bin/python sw/export_vectors.py results/models/${s}_H16_th256_k44_drop --n_bins $N --vbits 16 --obits 16 --out sim/vecfull_h16_$s > logs/vecfull_h16_$s.log 2>&1 &
  wait
done
echo "VECFULL DONE $(date)"
