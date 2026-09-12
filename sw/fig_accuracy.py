#!/usr/bin/env python3
"""Figures: (a) R2 per session vs NeuroBench baselines, (b) decoded vs true velocity trace with input raster."""
import json, sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parent))
from snn_int import IntSNN
ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "paper" / "figures"; FIG.mkdir(exist_ok=True)
SESS = ["indy_20160622_01", "indy_20160630_01", "indy_20170131_02"]
TAG = sys.argv[1] if len(sys.argv) > 1 else "_H64_th256_k44_drop"
# NeuroBench published baselines (examples/primate_reaching/*.py comments), Indy sessions in the same order
NB = {"ANN 2D (NeuroBench)": [0.6327, 0.5241, 0.6217], "SNN3 (NeuroBench)": [0.6968, 0.5772, 0.6517], "SNN2 streaming (NeuroBench)": [0.6774, 0.5011, 0.5994]}
import json as _json
_lin = []
for _s in SESS:
    _f = ROOT / "results/models" / f"{_s}_LIN_k4_drop/eval_int.json"
    _lin.append(_json.load(open(_f))["test_r2_int"] if _f.exists() else np.nan)
ours = [json.load(open(ROOT / "results/models" / f"{s}{TAG}" / "eval_int.json")) for s in SESS]
r2 = [o["test_r2_int"] for o in ours]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(6.4, 2.9))
x = np.arange(3); w = 0.17
ax.bar(x - 2 * w, _lin, w, label="this work: linear leaky integrator, no hidden layer (int8)", color="#e8c9a0", edgecolor="#8a6a30", linewidth=0.4)
ax.bar(x - w, NB["ANN 2D (NeuroBench)"], w, label="NeuroBench ANN 2D (float)", color="#dddddd", hatch="xx", edgecolor="#777777", linewidth=0.4)
ax.bar(x, NB["SNN3 (NeuroBench)"], w, label="NeuroBench SNN3 (float, 3 layers)", color="#bbbbbb", hatch="//", edgecolor="#666666", linewidth=0.4)
ax.bar(x + w, NB["SNN2 streaming (NeuroBench)"], w, label="NeuroBench SNN2 streaming (float)", color="#7f9fbf", hatch="..", edgecolor="#3f5f7f", linewidth=0.4)
ax.bar(x + 2 * w, r2, w, label="this work: int8 / int20 streaming SNN (bit-exact HW)", color="#c0504d", edgecolor="#802020", linewidth=0.4)
for i, v in enumerate(r2): ax.text(x[i] + 2 * w, v + 0.01, f"{v:.2f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels([s.replace("indy_", "") for s in SESS]); ax.set_ylabel("test $R^2$ (NeuroBench)")
ax.set_ylim(0, 0.95); ax.axhline(0.55, ls="--", lw=0.8, color="k", label="accuracy threshold used in this work (0.55)")
ax.legend(fontsize=6.5, loc="upper center", frameon=False, ncol=2, bbox_to_anchor=(0.5, -0.16))
fig.tight_layout(); fig.savefig(FIG / "r2.pdf", bbox_inches="tight"); fig.savefig(FIG / "r2.png", dpi=200, bbox_inches="tight")
print("mean R2 ours", np.mean(r2), "SNN2", np.mean(NB["SNN2 streaming (NeuroBench)"]), "SNN3", np.mean(NB["SNN3 (NeuroBench)"]))
# ---- trace figure
s = "indy_20160630_01"
m = np.load(ROOT / "results/models" / f"{s}{TAG}" / "model_int.npz"); d = np.load(ROOT / "data/prepared" / f"{s}.npz")
X = d["spikes"] > 0; V = d["vel"]; lo = int(d["ind_test"][0]); n = 2500  # 10 s
ref = IntSNN(m["W1"].astype(np.int64), m["W2"].astype(np.int64), int(m["theta"]), int(m["k1"]), int(m["k2"]))
Y, S = ref.run(X[lo:lo + n]); pred = (m["G"] * Y / 4096 + m["B"]) * m["vel_std"] + m["vel_mean"]
t = np.arange(n) * 0.004
fig, axs = plt.subplots(3, 1, figsize=(6.4, 4.2), sharex=True, gridspec_kw={"height_ratios": [1.6, 1, 1]})
r, c = np.nonzero(X[lo:lo + n]); axs[0].scatter(r * 0.004, c, s=0.6, color="k", marker="|", linewidths=0.4)
axs[0].set_ylabel("input channel"); axs[0].set_ylim(-1, 96)
axs[0].set_title(f"{s}: {X[lo:lo+n].sum()/n:.1f} input events/bin, {S.mean():.2f} hidden spikes/bin", fontsize=8)
for i, (ax, name) in enumerate(zip(axs[1:], ["$v_x$", "$v_y$"])):
    ax.plot(t, V[lo:lo + n, i], color="#555555", lw=0.9, label="measured")
    ax.plot(t, pred[:, i], color="#c0504d", lw=0.9, label="decoded (integer SNN)")
    ax.set_ylabel(name)
axs[1].legend(fontsize=7, frameon=False, ncol=2, loc="upper right"); axs[2].set_xlabel("time in test block (s)")
fig.tight_layout(); fig.savefig(FIG / "trace.pdf"); fig.savefig(FIG / "trace.png", dpi=200); print("figures written")
