#!/usr/bin/env python3
"""Round 5, figure F1: energy per bin against accuracy (integer-reference R2, mean over sessions and seeds, error bars = sd over seeds)
for the training grid hardened as 12-bit gated hardwired cores at 5 MHz (sky130). Marker size ~ H, colour ~ synapse density; the
Pareto front is drawn. Reads results/pareto.csv (sw/collect_pareto.py). Writes paper/figures/pareto.{pdf,png}, figures/pareto_points.csv."""
import csv, sys
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent
rows = [r for r in csv.DictReader(open(ROOT / "results/pareto.csv")) if r["energy_per_bin_nJ"] and r["r2_int_mean"]]
if not rows: sys.exit("no hardened grid points yet")
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(4.6, 3.2))
dens_col = {"1.0": "#c0504d", "0.5": "#e8a33d", "0.25": "#4f9d69", "0.125": "#7f9fbf"}
for r in rows:
    e = float(r["energy_per_bin_sdf_nJ"] or r["energy_per_bin_nJ"]); y = float(r["r2_int_mean"]); sd = float(r["r2_int_sd"]) if r["r2_int_sd"] else 0
    H = int(r["H"]); d = r["density"]
    ax.errorbar(e, y, yerr=sd, fmt="o", ms=3 + 1.6 * np.log2(H / 16 + 1), color=dens_col.get(d, "k"), mec="k", mew=0.4, elinewidth=0.7, capsize=1.5)
    ax.annotate(f"H={H}, {float(d)*100:g} %", (e, y), textcoords="offset points", xytext=(4, 3), fontsize=6)
front = sorted([r for r in rows if r["pareto"] == "True"], key=lambda r: float(r["energy_per_bin_sdf_nJ"] or r["energy_per_bin_nJ"]))
if len(front) > 1: ax.plot([float(r["energy_per_bin_sdf_nJ"] or r["energy_per_bin_nJ"]) for r in front], [float(r["r2_int_mean"]) for r in front], color="k", lw=0.8, ls="--", label="Pareto front")
ax.set_xscale("log"); ax.set_xlabel("energy per 4 ms bin (nJ), annotated where available"); ax.set_ylabel("test $R^2$ (integer reference, mean of 3 sessions x 5 seeds)")
ax.axhline(0.55, color="k", lw=0.6, ls=":"); ax.text(ax.get_xlim()[0] * 1.05, 0.551, "0.55", fontsize=6)
from matplotlib.lines import Line2D
h = [Line2D([], [], marker="o", color=c, ls="", mec="k", mew=0.4, label=f"{float(d)*100:g} % synapses") for d, c in dens_col.items()]
ax.legend(handles=h, fontsize=6.5, frameon=False, loc="lower right"); fig.tight_layout()
out = ROOT / "paper/figures"; fig.savefig(out / "pareto.pdf", bbox_inches="tight"); fig.savefig(out / "pareto.png", dpi=200, bbox_inches="tight")
with open(ROOT / "figures/pareto_points.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("wrote", out / "pareto.pdf", len(rows), "points")
