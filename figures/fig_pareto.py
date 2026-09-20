#!/usr/bin/env python3
"""Round 5, figure F1: energy per bin against decoding accuracy for every hardened core on sky130 at the common 5 MHz clock.
x: three-session mean test R2 (integer reference; grid points = mean over five seeds with min-max bars), linear 0.50-0.62.
y: energy per 4 ms bin with cell delays annotated (log, 1-3000 nJ). Marker shape = weight storage, colour = hidden width H.
Reads results/pareto.csv (E2 grid, sw/collect_pareto.py), results/designs.json (E1 cores, sw/collect_designs5.py),
results/raw/designs.json (50 MHz fallback for the latch core) and paper/numbers_software5.tex (hand-tuned software, E7).
Writes paper/figures/pareto.{pdf,png}, figures/pareto.{pdf,png} and figures/pareto_points.csv (the plotted data)."""
import csv, json, re, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT = Path(__file__).resolve().parent.parent
R2_THRESHOLD, R2_SNN2 = 0.55, 0.593
H_COL = {16: "#E69F00", 32: "#56B4E9", 64: "#009E73", 128: "#CC79A7"}          # Okabe-Ito, colourblind-safe
SHAPE = {"constants": "o", "latches": "s", "SRAM block": "D", "software": "*"}
LABEL_POS = {"bmi_snn_min": (0.5905, 13.5), "bmi_snn_ming": (0.5905, 8.2), "bmi_snn_m12": (0.5905, 5.0), "bmi_snn_lmin2_50MHz": (0.5905, 3.0),
             "bmi_snn_lmin2": (0.5905, 3.0), "bmi_snn_min32": (0.5905, 1.85)}
pts = []   # dicts: name, label, storage, H, density, r2, r2_min, r2_max, energy_nJ, energy_kind, note

def e_ann(rec, mode="event"):
    """annotated energy per bin (nJ) of a designs.json record, zero-delay as fallback"""
    s = rec.get(mode + "_sdf", {}).get("energy_per_bin_nJ"); z = rec.get(mode, {}).get("energy_per_bin_nJ")
    return (s, "annotated") if s else (z, "zero-delay")

# --- E2 grid (includes the E1 hardwired cores m12, sp, min32, min16 as grid members)
for r in csv.DictReader(open(ROOT / "results/pareto.csv")):
    if not (r["r2_int_mean"] and (r["energy_per_bin_sdf_nJ"] or r["energy_per_bin_nJ"])): continue
    e, kind = (float(r["energy_per_bin_sdf_nJ"]), "annotated") if r["energy_per_bin_sdf_nJ"] else (float(r["energy_per_bin_nJ"]), "zero-delay")
    H, d = int(r["H"]), float(r["density"])
    pts.append(dict(name=r["core"], label=f"{H}, {d*100:g} %", storage="constants", H=H, density=d, r2=float(r["r2_int_mean"]),
                    r2_min=float(r["r2_int_min"] or r["r2_int_mean"]), r2_max=float(r["r2_int_max"] or r["r2_int_mean"]), energy_nJ=e, energy_kind=kind,
                    note=f"{r['n_seeds']} seeds x 3 sessions, 12-bit gated hardwired core"))
# --- E1 cores that are not grid members
D = json.load(open(ROOT / "results/designs.json"))
def add_ref(name, label, storage, H, density, mode="event", note=""):
    if name not in D: return
    e, kind = e_ann(D[name], mode)
    if not e: return
    r2 = D[name]["r2"]
    pts.append(dict(name=name + ("" if mode == "event" else "_" + mode), label=label, storage=storage, H=H, density=density, r2=r2, r2_min=r2, r2_max=r2,
                    energy_nJ=e, energy_kind=kind, note=note or "released seed-0 models, bit-exact"))
add_ref("bmi_snn_min", "64, 100 %, 16-bit", "constants", 64, 1.0, note="16-bit state, no gating")
add_ref("bmi_snn_ming", "64, 100 %, 16-bit gated", "constants", 64, 1.0, note="16-bit state, gated datapath")
add_ref("bmi_snn_top", "SRAM, event mode", "SRAM block", 64, 1.0)
add_ref("bmi_snn_top", "SRAM, dense mode", "SRAM block", 64, 1.0, mode="dense", note="all synapses visited every bin")
add_ref("bmi_snn_topg", "SRAM, gated groups", "SRAM block", 64, 1.0)
# --- programmable latch core: 5 MHz record if present, otherwise the 50 MHz measurement (marked)
if "bmi_snn_lmin2" in D and e_ann(D["bmi_snn_lmin2"])[0]:
    add_ref("bmi_snn_lmin2", "latch memory", "latches", 64, 1.0)
else:
    R = json.load(open(ROOT / "results/raw/designs.json")).get("bmi_snn_lmin2", {})
    e, kind = e_ann(R)
    if e: pts.append(dict(name="bmi_snn_lmin2_50MHz", label="latch memory (50 MHz)", storage="latches", H=64, density=1.0, r2=R["r2"], r2_min=R["r2"], r2_max=R["r2"],
                          energy_nJ=e, energy_kind=kind, note="50 MHz netlist (rounds 1-4); the 5 MHz hardening did not close"))
# --- hand-tuned software on the RISC-V SoC (E7, per-pin method, 5 MHz)
m = re.search(r"\\newcommand\{\\eCpuTunedFive\}\{([\d,\.]+)\}", (ROOT / "paper/numbers_software5.tex").read_text())
if m: pts.append(dict(name="soc_tuned_5MHz", label="software, hand-tuned", storage="software", H=64, density=1.0, r2=D["bmi_snn_top"]["r2"], r2_min=D["bmi_snn_top"]["r2"],
                      r2_max=D["bmi_snn_top"]["r2"], energy_nJ=float(m.group(1).replace(",", "")), energy_kind="annotated", note="RISC-V SoC, decoding window, cell delays annotated"))
if not pts: sys.exit("no points")

plt.rcParams.update({"font.size": 8, "font.family": "sans-serif", "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(5.8, 3.5))
for p in pts:
    col = H_COL.get(p["H"], "k"); mk = SHAPE[p["storage"]]
    ax.errorbar(p["r2"], p["energy_nJ"], xerr=[[p["r2"] - p["r2_min"]], [p["r2_max"] - p["r2"]]], fmt=mk, ms=8 if mk == "*" else 5, color=col, mec="k", mew=0.4,
                elinewidth=0.7, capsize=1.5, ecolor=col, zorder=3)
    if p["name"] in LABEL_POS:   # crowded points: label placed in free space with a thin leader line
        xt, yt = LABEL_POS[p["name"]]
        ax.annotate(p["label"], (p["r2"], p["energy_nJ"]), xytext=(xt, yt), textcoords="data", fontsize=6, va="center", ha="left",
                    arrowprops=dict(arrowstyle="-", lw=0.4, color="0.55", shrinkA=0, shrinkB=2), zorder=4)
        continue
    dx, dy = (4, 3)
    if p["name"] in ("bmi_snn_g64p125", "bmi_snn_g128p125"): dx, dy = (-4, 5)
    if p["name"] == "bmi_snn_topg": dx, dy = (4, -8)
    if p["name"] == "bmi_snn_g64p50": dx, dy = (-4, 4)
    ax.annotate(p["label"], (p["r2"], p["energy_nJ"]), textcoords="offset points", xytext=(dx, dy), fontsize=6, ha="left" if dx > 0 else "right")
# lines: equal H across densities (hardwired 12-bit grid), and dense hardwired across H
grid = [p for p in pts if p["storage"] == "constants" and "16-bit" not in p["label"]]
for H in sorted({p["H"] for p in grid}):
    s = sorted([p for p in grid if p["H"] == H], key=lambda p: p["density"])
    if len(s) > 1: ax.plot([p["r2"] for p in s], [p["energy_nJ"] for p in s], color=H_COL.get(H, "k"), lw=0.8, ls="-", alpha=0.8, zorder=2)
dense = sorted([p for p in grid if p["density"] == 1.0], key=lambda p: p["H"])
if len(dense) > 1: ax.plot([p["r2"] for p in dense], [p["energy_nJ"] for p in dense], color="0.35", lw=0.8, ls="--", zorder=2)
ax.axvline(R2_THRESHOLD, color="k", lw=0.6, ls="--"); ax.text(R2_THRESHOLD - 0.0015, 150, "comparison\nthreshold 0.55", fontsize=6, ha="right", va="center")
ax.axvline(R2_SNN2, color="k", lw=0.6, ls="--"); ax.text(R2_SNN2 + 0.0015, 150, "NeuroBench SNN2\n(float) 0.593", fontsize=6, ha="left", va="center")
ax.set_yscale("log"); ax.set_xlim(0.50, 0.62); ax.set_ylim(1, 3000)
ax.set_xlabel("test $R^2$, three-session mean (integer reference)"); ax.set_ylabel("energy per 4 ms bin (nJ), cell delays annotated")
hH = [Line2D([], [], marker="o", color=c, ls="", mec="k", mew=0.4, label=f"H = {H}") for H, c in H_COL.items() if any(p["H"] == H for p in pts)]
hS = [Line2D([], [], marker=mk, color="0.6", ls="", mec="k", mew=0.4, ms=8 if mk == "*" else 5, label=st) for st, mk in SHAPE.items() if any(p["storage"] == st for p in pts)]
hL = [Line2D([], [], color="0.5", lw=0.8, label="equal H, density varied"), Line2D([], [], color="0.35", lw=0.8, ls="--", label="dense, H varied")]
ax.legend(handles=hH + hS + hL, fontsize=6, frameon=False, loc="upper left", ncol=2, columnspacing=0.8, handletextpad=0.4)
fig.tight_layout()
for out in (ROOT / "paper/figures", ROOT / "figures"):
    out.mkdir(exist_ok=True); fig.savefig(out / "pareto.pdf", bbox_inches="tight"); fig.savefig(out / "pareto.png", dpi=200, bbox_inches="tight")
with open(ROOT / "figures/pareto_points.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(pts[0].keys())); w.writeheader(); w.writerows(pts)
print("wrote", out / "pareto.pdf", len(pts), "points")
