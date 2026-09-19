#!/usr/bin/env python3
"""Round 5, figure F2: average power against decode rate (bins per second) for every kit, clock stopped between bins:
P(rate) = E_dyn x rate + leakage (total leakage solid, logic-only leakage dashed), one panel per core hardened on several kits.
Reads results/pdks5.json (sw/collect_pdks5.py). Writes paper/figures/pavg_vs_rate.{pdf,png} and figures/pavg_vs_rate.csv."""
import json, csv, sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent
P = json.load(open(ROOT / "results/pdks5.json"))
KITS = [("sky130", "SkyWater 130 nm", "#c0504d"), ("gf180", "GF 180 nm (5 V)", "#e8a33d"), ("ihp", "IHP 130 nm", "#7f9fbf"), ("nangate45", "NanGate 45 nm (pred.)", "#777777"),
        ("asap7", "ASAP7 RVT (pred.)", "#4f9d69"), ("asap7sram", "ASAP7 SRAM-Vt (pred.)", "#1f5f3f")]
CORES = [c for c in ("sp", "m12", "min32", "min16") if any(f"{k}/{c}" in P for k, _, _ in KITS)]
rates = np.logspace(0, 3, 200)
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, axs = plt.subplots(1, len(CORES), figsize=(1.9 + 2.4 * len(CORES), 2.9), sharey=True, squeeze=False); axs = axs[0]
rows = []
for ax, core in zip(axs, CORES):
    for kit, label, col in KITS:
        d = P.get(f"{kit}/{core}")
        if not d or not d.get("event") or not d.get("idle"): continue
        ed = d["energy_dyn_per_bin_nJ"]; lk = d["idle"]["leakage_uW"]; ll = (d.get("leak_split") or {}).get("leak_logic_uW")
        ax.plot(rates, ed * rates * 1e-3 + lk, color=col, lw=1.3, label=label)
        if ll is not None and ll < lk * 0.98: ax.plot(rates, ed * rates * 1e-3 + ll, color=col, lw=0.9, ls="--")
        rows.append({"core": core, "kit": kit, "energy_dyn_per_bin_nJ": ed, "leakage_total_uW": lk, "leakage_logic_uW": ll, "p_avg_250Hz_uW": ed * 0.25 + lk})
    ax.axvline(250, color="k", lw=0.6, ls=":"); ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("decode rate (bins/s)")
    ax.set_title({"sp": "pruned 12-bit core (sp)", "m12": "12-bit gated core (m12)", "min32": "H=32 core", "min16": "H=16 core"}[core], fontsize=8)
axs[0].set_ylabel("average power (µW), clock stopped between bins")
h, l = axs[0].get_legend_handles_labels()
for ax in axs[1:]:
    for hh, ll in zip(*ax.get_legend_handles_labels()):
        if ll not in l: h.append(hh); l.append(ll)
fig.legend(h, l, fontsize=6.8, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.02))
fig.text(0.99, 0.02, "solid: total leakage; dashed: logic-cell leakage only; dotted line: 250 bins/s", ha="right", fontsize=6.5)
fig.tight_layout(rect=(0, 0.1, 1, 1))
out = ROOT / "paper/figures"; fig.savefig(out / "pavg_vs_rate.pdf", bbox_inches="tight"); fig.savefig(out / "pavg_vs_rate.png", dpi=200, bbox_inches="tight")
with open(ROOT / "figures/pavg_vs_rate.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("wrote", out / "pavg_vs_rate.pdf", len(rows), "curves")
