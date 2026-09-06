#!/usr/bin/env python3
"""Full-test-set evaluation of a trained integer model with the pure-integer reference (snn_int.py).
Writes <model>/eval_int.json: NeuroBench R2 on the test block, activity statistics, cycle model."""
import json, sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snn_int import IntSNN, r2_neurobench
ROOT = Path(__file__).resolve().parent.parent
for mdir in [Path(p) for p in sys.argv[1:]]:
    m = np.load(mdir / "model_int.npz"); meta = json.load(open(mdir / "train.json"))
    d = np.load(ROOT / "data" / "prepared" / f"{meta['session']}.npz")
    X = d["spikes"] > 0; V = d["vel"]; ite = d["ind_test"]; lo, hi = int(ite[0]), int(ite[-1]) + 1
    ref = IntSNN(m["W1"].astype(np.int64), m["W2"].astype(np.int64), int(m["theta"]), int(m["k1"]), int(m["k2"]))
    t0 = time.time(); Y, S = ref.run(X[lo:hi]); dt = time.time() - t0
    pred = (m["G"] * Y / 4096.0 + m["B"]) * m["vel_std"] + m["vel_mean"]
    r2 = r2_neurobench(pred, V[lo:hi])
    nev = X[lo:hi].sum(1); H = m["W1"].shape[1]
    cyc_ev = 17 * nev + (17 + H + 2)            # per-bin active cycles, event mode (17/event row, bias row, scan, out)
    cyc_dn = nev + 97 * 17 + H + 2               # dense mode
    res = {"session": meta["session"], "model": str(mdir), "test_bins": int(hi - lo), "test_r2_int": r2,
           "test_r2_torch": meta["test_r2"], "val_r2": meta["val_r2"],
           "events_per_bin": float(nev.mean()), "events_per_bin_std": float(nev.std()), "events_per_bin_max": int(nev.max()),
           "input_sparsity": float(1 - nev.mean() / 96), "hidden_spikes_per_bin": float(S.mean()),
           "hidden_sparsity": float(1 - S.mean() / H), "H": int(H), "theta": int(m["theta"]), "k1": int(m["k1"]), "k2": int(m["k2"]),
           "synops_per_bin_event": float(nev.mean() * H + H + S.mean() * 2), "synops_per_bin_dense": float(97 * H + S.mean() * 2),
           "cycles_per_bin_event_model": float(cyc_ev.mean()), "cycles_per_bin_dense_model": float(cyc_dn.mean()),
           "weights_bytes": int(97 * H + 2 * H), "eval_seconds": dt}
    json.dump(res, open(mdir / "eval_int.json", "w"), indent=1)
    print(f"{meta['session']}: test R2(int) {r2:.4f} (torch {meta['test_r2']:.4f}), events/bin {nev.mean():.2f}, "
          f"hidden spk/bin {S.mean():.2f}, cycles/bin event {cyc_ev.mean():.0f} dense {cyc_dn.mean():.0f}")
