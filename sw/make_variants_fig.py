#!/usr/bin/env python3
"""Regenerate paper/figures/variants.{pdf,png} from results/designs.json with numbered, non-overlapping labels.
Drop-in replacement for make_variant_figure() in sw/collect_designs.py (same data, same colours/markers)."""
import json, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = sys.argv[1]; OUT = sys.argv[2]
out = json.load(open(f"{REPO}/results/designs.json"))
ORDER = ["bmi_snn_top", "bmi_snn_topg", "bmi_snn_scmem", "bmi_snn_lmem", "bmi_snn_lmem2", "bmi_snn_lmin2",
         "bmi_snn_hw", "bmi_snn_min", "bmi_snn_ming", "bmi_snn_m12", "bmi_snn_sp", "bmi_snn_min32", "bmi_snn_min16"]
SHORT = {"bmi_snn_top": "SRAM, sequential", "bmi_snn_topg": "SRAM, gated membrane groups",
         "bmi_snn_scmem": "flip-flop register file", "bmi_snn_lmem": "latch memory",
         "bmi_snn_lmem2": "latch memory, pipelined W$_2$", "bmi_snn_lmin2": "latch mem., gated, 12 b, pipel.",
         "bmi_snn_hw": "hardwired 20 b", "bmi_snn_min": "hardwired 16 b", "bmi_snn_ming": "hardwired 16 b, gated",
         "bmi_snn_m12": "hardwired 12 b, gated", "bmi_snn_sp": "hardwired 12 b, gated, 25 % syn.",
         "bmi_snn_min32": "hardwired 16 b, H = 32", "bmi_snn_min16": "hardwired 16 b, H = 16"}
names = [n for n in ORDER if n in out and "event" in out[n]]
col = {"seq": "#c0504d", "prog": "#7f6fbf", "hw": "#2e7d5b"}
mk = {"seq": "s", "prog": "D", "hw": "o"}
def E(n): d = out[n]; return d.get("event_sdf", d["event"])["energy_per_bin_nJ"]
def A(n): return out[n]["pnr"]["instance_area_um2"] / 1e6

plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, axs = plt.subplots(1, 2, figsize=(6.6, 3.0))

def place(ax, xs, ys, logx):
    """Greedy label placement: choose, per point, the candidate offset (in points) that maximises the distance
    to all markers and to all labels placed so far."""
    fig.canvas.draw()
    tr = ax.transData
    pts = np.array([tr.transform((x, y)) for x, y in zip(xs, ys)])  # display px
    px_per_pt = fig.dpi / 72.0
    cands = [(4, 3), (-4, 3), (4, -4), (-4, -4), (6, 0), (-6, 0), (0, 5), (0, -6), (7, 5), (-7, 5), (7, -6), (-7, -6)]
    def anchor(i, c):  # approximate label centre in px
        return pts[i] + np.array(c) * px_per_pt + np.array([4 if c[0] > 0 else (-4 if c[0] < 0 else 0), 3 if c[1] > 0 else (-3 if c[1] < 0 else 0)]) * px_per_pt
    placed = []; off = [None] * len(xs)
    T = 11 * px_per_pt   # minimum clearance (pt) between a label and any marker or other label
    order = sorted(range(len(xs)), key=lambda i: (round(xs[i], 4), ys[i]))
    for i in order:
        chosen = None; fallback, fscore = cands[0], -1e9
        for c in cands:
            a = anchor(i, c)
            dm = min(np.hypot(*(a - pts[j])) for j in range(len(xs)) if j != i)
            dl = min([np.hypot(*(a - q)) for q in placed] + [1e9])
            sc = min(dm, dl)
            if sc >= T: chosen = c; break
            if sc > fscore: fallback, fscore = c, sc
        off[i] = chosen if chosen is not None else fallback
        placed.append(anchor(i, off[i]))
    return off

for k, ax in enumerate(axs):
    xs = [A(n) if k == 0 else out[n]["r2"] for n in names]; ys = [E(n) for n in names]
    for n, x, y in zip(names, xs, ys):
        fam = out[n]["family"]
        ax.scatter(x, y, c=col[fam], marker=mk[fam], s=30, zorder=3, edgecolor="white", linewidth=0.5)
    ax.set_yscale("log")
    if k == 0:
        ax.set_xscale("log"); ax.set_xlabel("instance area (mm²)")
        ax.set_ylabel("energy per 4 ms bin (nJ)")
    else:
        ax.set_xlabel("test R² (mean of three sessions)"); ax.set_xlim(0.548, 0.597)
        ax.axvline(0.55, color="0.6", ls=":", lw=0.8)
    ax.set_ylim(1.5, 70)
    if k == 0:
        offs = place(ax, xs, ys, True)
        for i, (n, x, y) in enumerate(zip(names, xs, ys)):
            ax.annotate(str(i + 1), (x, y), fontsize=7, xytext=offs[i], textcoords="offset points",
                        ha="left" if offs[i][0] > 0 else "right", va="bottom" if offs[i][1] > 0 else "top")
    else:
        # right panel: many cores share R2 = 0.583, so label clusters with a joined list of numbers
        fig.canvas.draw(); tr = ax.transData
        pts = np.array([tr.transform((x, y)) for x, y in zip(xs, ys)])
        groups = []
        for i in np.argsort(-np.array(ys)):
            for g in groups:
                if np.hypot(*(pts[i] - pts[g[0]])) < 9 * fig.dpi / 72: g.append(i); break
            else: groups.append([i])
        side = 1
        for g in sorted(groups, key=lambda g: -ys[g[0]]):
            gx = np.mean([xs[i] for i in g]); gy = np.exp(np.mean([np.log(ys[i]) for i in g]))
            lab = ", ".join(str(i + 1) for i in sorted(g))
            if len(g) > 1: side = -side
            dx = 6 * side if len(g) > 1 else 5
            ax.annotate(lab, (gx, gy), fontsize=7, xytext=(dx, 0), textcoords="offset points",
                        ha="left" if dx > 0 else "right", va="center")
for fam, lab in (("seq", "SRAM macro, sequential"), ("prog", "weights in standard cells"), ("hw", "hardwired weights")):
    axs[0].scatter([], [], c=col[fam], marker=mk[fam], s=30, label=lab)
axs[0].legend(fontsize=7, frameon=False, loc="lower right")
# key below the panels, three columns
key = [f"{i+1}  {SHORT[n]}" for i, n in enumerate(names)]
ncol = 3; rows = int(np.ceil(len(key) / ncol))
fig.subplots_adjust(bottom=0.40, wspace=0.30, left=0.10, right=0.99, top=0.97)
for c in range(ncol):
    txt = "\n".join(key[c * rows:(c + 1) * rows])
    fig.text(0.05 + c * 0.33, 0.24, txt, fontsize=7, va="top", ha="left", linespacing=1.35)
fig.savefig(f"{OUT}/variants.pdf"); fig.savefig(f"{OUT}/variants.png", dpi=200)
print("written", len(names), "points")
