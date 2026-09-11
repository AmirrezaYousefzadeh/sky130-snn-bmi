#!/usr/bin/env python3
"""Quantisation-exact training of the integer streaming SNN (see snn_int.py) with surrogate gradients.

Forward pass is bit-exact with the integer model (weights rounded with STE, leak uses floor with STE,
all values stay integer-valued in float32), so the trained network needs no post-training calibration.
"""
from __future__ import annotations
import argparse, json, math, time
from pathlib import Path
import numpy as np, torch, torch.nn as nn
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snn_int import IntSNN, r2_neurobench, N_IN, V_MAX, O_MAX

ROOT = Path(__file__).resolve().parent.parent


class RoundSTE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x): return torch.round(x)
    @staticmethod
    def backward(ctx, g): return g

class FloorSTE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x): return torch.floor(x)
    @staticmethod
    def backward(ctx, g): return g

class SpikeFn(torch.autograd.Function):
    """Heaviside(x) with fast-sigmoid surrogate; x is (vl - theta) / theta."""
    scale = 5.0
    @staticmethod
    def forward(ctx, x):
        ctx.save_for_backward(x)
        return (x >= 0).to(x.dtype)
    @staticmethod
    def backward(ctx, g):
        (x,) = ctx.saved_tensors
        return g / (SpikeFn.scale * x.abs() + 1.0) ** 2


class QSNN(nn.Module):
    def __init__(self, H, theta, k1, k2, w_init=40.0, drop=0.0, wbits=8, n_in=N_IN):
        super().__init__()
        self.H, self.theta, self.k1, self.k2, self.n_in = H, theta, k1, k2, n_in
        N_IN = n_in
        self.wmax = 2 ** (wbits - 1) - 1
        self.w1 = nn.Parameter(torch.randn(N_IN + 1, H) * w_init)   # row 96 = bias
        self.w1.data[N_IN] = 0.0
        self.w2 = nn.Parameter(torch.randn(H, 2) * w_init)
        self.g = nn.Parameter(torch.ones(2))
        self.b = nn.Parameter(torch.zeros(2))
        self.drop = nn.Dropout(drop) if drop > 0 else nn.Identity()
        self.register_buffer("mask1", torch.ones(N_IN + 1, H))          # magnitude-pruning mask of W1 (1 = kept)

    def qweights(self):
        return RoundSTE.apply(self.w1.clamp(-self.wmax, self.wmax)) * self.mask1, RoundSTE.apply(self.w2.clamp(-self.wmax, self.wmax))

    def prune_to(self, density):
        """Keep the `density` fraction of largest-magnitude W1 synapses (rows 0..95; the bias row is never pruned)."""
        with torch.no_grad():
            w = (self.w1[:self.n_in].abs() * self.mask1[:self.n_in]).flatten()
            k = int(round(density * w.numel()))
            thr = torch.topk(w, k).values.min() if k > 0 else w.max() + 1
            self.mask1[:self.n_in] = ((self.w1[:self.n_in].abs() >= thr) & (self.mask1[:self.n_in] > 0)).float()
            self.w1[:self.n_in] *= self.mask1[:self.n_in]
            return float(self.mask1[:self.n_in].mean())

    def forward(self, x):
        """x: (B, T, 96) float {0,1}. Returns yhat (B,T,2) in normalised velocity units, hidden spikes (B,T,H)."""
        W1, W2 = self.qweights()
        B, T, _ = x.shape
        v = torch.zeros(B, self.H, device=x.device)
        o = torch.zeros(B, 2, device=x.device)
        ys, ss = [], []
        xb = torch.cat([x, torch.ones(B, T, 1, device=x.device)], dim=2)   # bias input
        cur = xb @ W1                                                     # (B,T,H) integer-valued
        for t in range(T):
            v = (v + self.drop(cur[:, t])).clamp(-V_MAX - 1, V_MAX)
            vl = v - FloorSTE.apply(v / 2 ** self.k1)
            s = SpikeFn.apply((vl - self.theta) / self.theta)
            v = vl * (1 - s)
            o = (o - FloorSTE.apply(o / 2 ** self.k2) + s @ W2).clamp(-O_MAX - 1, O_MAX)
            ys.append(o); ss.append(s)
        y = torch.stack(ys, 1)
        yhat = self.g * y / 4096.0 + self.b
        return yhat, torch.stack(ss, 1), y


def load_session(name):
    d = np.load(ROOT / "data" / "prepared" / f"{name}.npz")
    return d["spikes"].astype(np.float32), d["vel"].astype(np.float32), d["ind_train"], d["ind_val"], d["ind_test"]


def contiguous(ind):
    assert np.all(np.diff(ind) == 1), "expected contiguous block"
    return int(ind[0]), int(ind[-1]) + 1


def evaluate(model, X, Vn, lo, hi, device, chunk=8192):
    """Run continuously over [lo,hi) from zero state; return R2 (normalised units == original units)."""
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(X[lo:hi]).to(device)[None]
        # run in one long sequence (state carried across chunks)
        W1, W2 = model.qweights()
        v = torch.zeros(1, model.H, device=device); o = torch.zeros(1, 2, device=device)
        ys = []; nsp = 0
        xb = torch.cat([x, torch.ones(1, x.shape[1], 1, device=device)], 2)
        cur = xb @ W1
        for t in range(x.shape[1]):
            v = (v + cur[:, t]).clamp(-V_MAX - 1, V_MAX)
            vl = v - torch.floor(v / 2 ** model.k1)
            s = (vl >= model.theta).float()
            v = vl * (1 - s)
            o = (o - torch.floor(o / 2 ** model.k2) + s @ W2).clamp(-O_MAX - 1, O_MAX)
            ys.append(o); nsp += s.sum().item()
        y = torch.stack(ys, 1)
        yhat = (model.g * y / 4096.0 + model.b)[0].cpu().numpy()
    r2 = r2_neurobench(yhat, Vn[lo:hi])
    return r2, nsp / (hi - lo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="indy_20160630_01")
    ap.add_argument("--H", type=int, default=64)
    ap.add_argument("--theta", type=int, default=1024)
    ap.add_argument("--k1", type=int, default=4)
    ap.add_argument("--k2", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=600, help="number of gradient steps")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--eval_every", type=int, default=50)
    ap.add_argument("--L", type=int, default=256, help="chunk length (bins)")
    ap.add_argument("--warm", type=int, default=64)
    ap.add_argument("--lr", type=float, default=2.0)
    ap.add_argument("--drop", type=float, default=0.0)
    ap.add_argument("--w_init", type=float, default=40.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--wbits", type=int, default=8)
    ap.add_argument("--prune", type=float, default=1.0, help="final density of W1 (fraction of non-zero synapses)")
    ap.add_argument("--prune_start", type=float, default=0.2, help="fraction of steps before pruning starts")
    ap.add_argument("--prune_end", type=float, default=0.6, help="fraction of steps at which the final density is reached")
    ap.add_argument("--prune_every", type=int, default=50)
    ap.add_argument("--init_from", type=Path, default=None, help="load W1/W2 from this model directory (model_int.npz)")
    ap.add_argument("--train_only", default="all", choices=["all", "bias_w2"],
                    help="bias_w2: keep the 96 input rows of W1 fixed (hybrid core: hardwired W1, programmable bias and read-out)")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    torch.manual_seed(a.seed); np.random.seed(a.seed)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    X, V, itr, iva, ite = load_session(a.session)
    tr_lo, tr_hi = contiguous(itr); va_lo, va_hi = contiguous(iva); te_lo, te_hi = contiguous(ite)
    mu, sd = V[tr_lo:tr_hi].mean(0), V[tr_lo:tr_hi].std(0)
    Vn = ((V - mu) / sd).astype(np.float32)

    n_in = X.shape[1]                                   # 96 channels (Indy) or 192 (Loco)
    model = QSNN(a.H, a.theta, a.k1, a.k2, a.w_init, a.drop, a.wbits, n_in=n_in).to(dev)
    if a.init_from is not None:
        m0 = np.load(a.init_from / "model_int.npz")
        with torch.no_grad():
            model.w1.copy_(torch.from_numpy(m0["W1"].astype(np.float32))); model.w2.copy_(torch.from_numpy(m0["W2"].astype(np.float32)))
            model.mask1.copy_((model.w1 != 0).float()); model.mask1[model.n_in] = 1.0
            if "G" in m0: model.g.copy_(torch.from_numpy(m0["G"].astype(np.float32))); model.b.copy_(torch.from_numpy(m0["B"].astype(np.float32)))
        print(f"initialised from {a.init_from} (W1 density {float((m0['W1'][:model.n_in] != 0).mean()):.3f})")
    opt = torch.optim.Adam([{"params": [model.w1, model.w2], "lr": a.lr},
                            {"params": [model.g, model.b], "lr": 1e-2}])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, a.epochs, eta_min=a.lr * 0.05)
    Xtr = torch.from_numpy(X[tr_lo:tr_hi]).to(dev); Ytr = torch.from_numpy(Vn[tr_lo:tr_hi]).to(dev)
    n_tr = tr_hi - tr_lo
    Xva = torch.from_numpy(X[va_lo:va_hi]).to(dev); Yva = torch.from_numpy(Vn[va_lo:va_hi]).to(dev)

    def batched_r2(Xs, Ys, L=2048):
        """Fast validation: chunks of L run in parallel from zero state (state reset each chunk)."""
        model.eval()
        with torch.no_grad():
            n = (Xs.shape[0] // L) * L
            xb = Xs[:n].reshape(-1, L, model.n_in); yb = Ys[:n].reshape(-1, L, 2)
            yhat, s, _ = model(xb)
            r2 = r2_neurobench(yhat.reshape(-1, 2).cpu().numpy(), yb.reshape(-1, 2).cpu().numpy())
            return r2, s.sum(2).mean().item()

    best = (-1e9, None); hist = []
    t0 = time.time()
    steps = a.epochs
    for step in range(steps):
        model.train()
        starts = torch.randint(0, n_tr - a.L, (a.batch,), device=dev)
        idx = starts[:, None] + torch.arange(a.L, device=dev)[None]
        xb, yb = Xtr[idx], Ytr[idx]
        yhat, s, _ = model(xb)
        loss = ((yhat[:, a.warm:] - yb[:, a.warm:]) ** 2).mean()
        opt.zero_grad(); loss.backward()
        if a.train_only == "bias_w2": model.w1.grad[:model.n_in] = 0.0     # only the bias row of W1, W2, g and b are adapted
        opt.step(); sched.step()
        if a.prune < 1.0 and step % a.prune_every == 0:
            s0, s1 = int(a.prune_start * steps), int(a.prune_end * steps)
            if s0 <= step <= s1:
                frac = (step - s0) / max(1, s1 - s0)
                target = 1.0 - (1.0 - a.prune) * (1.0 - (1.0 - frac) ** 3)
                dens = model.prune_to(target)
                if step % (a.prune_every * 4) == 0: print(f"step {step:5d} pruned W1 to density {dens:.3f}", flush=True)
        if step % a.eval_every == a.eval_every - 1 or step == steps - 1:
            r2v, spv = batched_r2(Xva, Yva)
            hist.append({"step": step + 1, "loss": loss.item(), "val_r2_batched": r2v, "hidden_spikes_per_bin": spv})
            print(f"step {step+1:5d} loss {loss.item():.4f} val R2(batched) {r2v:.4f} hid.spk/bin {spv:.2f} "
                  f"train hid.rate {s.mean().item():.4f} ({time.time()-t0:.0f}s)", flush=True)
            # with pruning, only checkpoints taken after the final density has been reached are eligible (an earlier,
            # less pruned checkpoint would be pruned abruptly at export and lose its accuracy)
            eligible = a.prune >= 1.0 or step + 1 > int(a.prune_end * steps)
            if eligible and r2v > best[0]:
                best = (r2v, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()})
    model.load_state_dict(best[1])
    r2v, spv = evaluate(model, X, Vn, va_lo, va_hi, dev)
    r2t, spt = evaluate(model, X, Vn, te_lo, te_hi, dev)
    print(f"BEST val R2 {r2v:.4f} | TEST R2 {r2t:.4f} | hidden spikes/bin (test) {spt:.2f}")

    # ---- cross-check against the pure-integer numpy model on a slice --------------------------
    if a.prune < 1.0: model.prune_to(a.prune)
    W1, W2 = model.qweights(); W1 = W1.detach().cpu().numpy().astype(np.int64); W2 = W2.detach().cpu().numpy().astype(np.int64)
    density = float((W1[:n_in] != 0).mean()); print(f"W1 density (non-zero synapses, input rows): {density:.3f}")
    ref = IntSNN(W1, W2, a.theta, a.k1, a.k2)
    n_chk = 3000
    Yref, _ = ref.run(X[te_lo:te_lo + n_chk] > 0.5)
    with torch.no_grad():
        _, _, ytorch = model(torch.from_numpy(X[te_lo:te_lo + n_chk]).to(dev)[None])
    mism = int((Yref != ytorch[0].cpu().numpy().astype(np.int64)).sum())
    print(f"integer cross-check on {n_chk} bins: mismatching outputs = {mism}")

    out = a.out or (ROOT / "results" / "models" / f"{a.session}_H{a.H}_th{a.theta}_k{a.k1}{a.k2}{a.tag}")
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / "model_int.npz", W1=W1.astype(np.int8), W2=W2.astype(np.int8), theta=a.theta, k1=a.k1, k2=a.k2,
             G=model.g.detach().cpu().numpy(), B=model.b.detach().cpu().numpy(), vel_mean=mu, vel_std=sd)
    json.dump({"session": a.session, "H": a.H, "theta": a.theta, "k1": a.k1, "k2": a.k2, "epochs": a.epochs,
               "L": a.L, "lr": a.lr, "drop": a.drop, "seed": a.seed, "wbits": a.wbits, "val_r2": r2v, "test_r2": r2t,
               "hidden_spikes_per_bin_test": spt, "int_crosscheck_mismatches": mism, "prune": a.prune, "w1_density": density,
               "init_from": str(a.init_from) if a.init_from else None, "train_only": a.train_only,
               "train_bins": int(n_tr), "val_bins": int(va_hi - va_lo), "test_bins": int(te_hi - te_lo),
               "history": hist}, open(out / "train.json", "w"), indent=1)
    print("saved", out)

if __name__ == "__main__":
    main()
