#!/usr/bin/env python3
"""Export weights.hex / stream.hex / expect.hex for tb_bmi_snn from a trained model_int.npz.

Also writes stats.json with the reference model's activity statistics over the exported slice.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snn_int import IntSNN, r2_neurobench, N_IN
ROOT = Path(__file__).resolve().parent.parent

ap = argparse.ArgumentParser()
ap.add_argument("model", type=Path, help="dir containing model_int.npz")
ap.add_argument("--session", default=None)
ap.add_argument("--start", type=int, default=0, help="offset into the test block")
ap.add_argument("--n_bins", type=int, default=2000)
ap.add_argument("--out", type=Path, required=True)
a = ap.parse_args()

m = np.load(a.model / "model_int.npz")
meta = json.load(open(a.model / "train.json"))
session = a.session or meta["session"]
d = np.load(ROOT / "data" / "prepared" / f"{session}.npz")
X = d["spikes"] > 0; V = d["vel"]; ite = d["ind_test"]
te_lo = int(ite[0])
lo = te_lo + a.start; hi = lo + a.n_bins
ref = IntSNN(m["W1"].astype(np.int64), m["W2"].astype(np.int64), int(m["theta"]), int(m["k1"]), int(m["k2"]))
Y, S = ref.run(X[lo:hi])

a.out.mkdir(parents=True, exist_ok=True)
mem = ref.memory_words()
(a.out / "weights.hex").write_text("\n".join(f"{w:08x}" for w in mem) + "\n")
toks = []
for t in range(lo, hi):
    toks += [f"{c:02x}" for c in np.flatnonzero(X[t])]
    toks.append("ff")
(a.out / "stream.hex").write_text("\n".join(toks) + "\n")
(a.out / "expect.hex").write_text("\n".join(f"{int(y) & 0xFFFFFFFF:08x}" for y in Y.reshape(-1)) + "\n")
nev = X[lo:hi].sum(1)
# post-map prediction + R2 on this slice (for information)
G, B, mu, sd = m["G"], m["B"], m["vel_mean"], m["vel_std"]
pred = (G * Y / 4096.0 + B) * sd + mu
stats = {"session": session, "test_block_start": te_lo, "slice": [lo, hi], "n_bins": a.n_bins,
         "input_events": int(nev.sum()), "events_per_bin_mean": float(nev.mean()), "events_per_bin_max": int(nev.max()),
         "hidden_spikes_total": int(S.sum()), "hidden_spikes_per_bin_mean": float(S.mean()),
         "H": int(m["W1"].shape[1]), "theta": int(m["theta"]), "k1": int(m["k1"]), "k2": int(m["k2"]),
         "slice_r2": r2_neurobench(pred, V[lo:hi]),
         "predicted_cycles_event_mode": int(17 * nev.sum() + a.n_bins * (17 + int(m["W1"].shape[1]) + 2)),
         "predicted_cycles_dense_mode": int(a.n_bins * (97 * 17 + int(m["W1"].shape[1]) + 2) + nev.sum())}
json.dump(stats, open(a.out / "stats.json", "w"), indent=1)
print(json.dumps(stats, indent=1))
