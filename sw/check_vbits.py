#!/usr/bin/env python3
"""Accuracy of the trained H=64 models when the membrane / output accumulators are narrower (saturating)."""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import snn_int
from snn_int import IntSNN, r2_neurobench
ROOT = Path(__file__).resolve().parent.parent
sessions = ['indy_20160622_01', 'indy_20160630_01', 'indy_20170131_02']
tag = sys.argv[1] if len(sys.argv) > 1 else 'H64_th256_k44_drop'
out = {}
for vb, ob in [(20, 24), (16, 16), (14, 16), (13, 16), (12, 16), (12, 14), (11, 14)]:
    snn_int.V_MAX = 2 ** (vb - 1) - 1; snn_int.O_MAX = 2 ** (ob - 1) - 1
    r2s = []
    for s in sessions:
        m = np.load(ROOT / 'results/models' / f'{s}_{tag}' / 'model_int.npz')
        d = np.load(ROOT / 'data/prepared' / f'{s}.npz'); X = d['spikes'] > 0; V = d['vel']; ite = d['ind_test']; lo, hi = int(ite[0]), int(ite[-1]) + 1
        ref = IntSNN(m['W1'].astype(np.int64), m['W2'].astype(np.int64), int(m['theta']), int(m['k1']), int(m['k2']))
        Y, S = ref.run(X[lo:hi]); pred = (m['G'] * Y / 4096.0 + m['B']) * m['vel_std'] + m['vel_mean']
        r2s.append(r2_neurobench(pred, V[lo:hi]))
    out[f'v{vb}_o{ob}'] = dict(r2=r2s, mean=float(np.mean(r2s)))
    print(f'V_BITS={vb} O_BITS={ob}: ' + ' '.join(f'{r:.4f}' for r in r2s) + f'  mean {np.mean(r2s):.4f}', flush=True)
json.dump(out, open(ROOT / 'results/explore' / f'vbits_{tag}.json', 'w'), indent=1)
