#!/usr/bin/env python3
"""Round 5, figure F3: (left) annotated power while decoding split into clock network, sequential cells, combinational cells and
memory block, normalized to 100 %, with the absolute energy per bin printed above each bar; (right) average power at 250 bins/s
with the clock stopped, split into dynamic (E_bin x 250/s) and leakage at 25 C, with a marker for the leakage interpolated to
37 C (exponential interpolation between the 25 C and 100 C typical liberties when the 100 C idle run exists). Reads
results/designs.json (5 MHz, sw/collect_designs5.py) and power/out_vcd_<design>_5m_idle_full_tt_100C_1v80/power_vcd.rpt.
Writes paper/figures/power_breakdown5.{pdf,png} and figures/power_breakdown5.csv."""
import json, csv, sys, math
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(ROOT := Path(__file__).resolve().parent.parent) and str(Path(__file__).resolve().parent.parent / "sw"))
from collect_results import parse_group_table, RATE
D = json.load(open(ROOT / "results/designs.json"))
ORDER = [("bmi_snn_top", "SRAM seq."), ("bmi_snn_top", "SRAM seq., dense", "dense"), ("bmi_snn_topg", "SRAM seq. gated"), ("bmi_snn_lmin2", "latch 12-bit"), ("bmi_snn_hw", "hardwired 20-bit"), ("bmi_snn_min", "hw 16-bit"),
         ("bmi_snn_ming", "hw 16-bit gated"), ("bmi_snn_m12", "hw 12-bit gated"), ("bmi_snn_sp", "pruned 25 %"), ("bmi_snn_min32", "H=32"), ("bmi_snn_min16", "H=16")]
items = []
for entry in ORDER:
    name, label = entry[0], entry[1]; mode = entry[2] if len(entry) > 2 else "event"
    d = D.get(name)
    if not d or not d.get(mode): continue
    e = d.get(mode + "_sdf") or d[mode]; g = e["groups"]; tot = g["Total"]["total"]
    parts = {k: g.get(k, {}).get("total", 0) / tot for k in ("Clock", "Sequential", "Combinational", "Macro")}
    leak = d.get("idle", {}).get("leakage_uW"); E = e["energy_per_bin_nJ"]
    l100 = None; f = ROOT / f"power/out_vcd_{name}_5m_idle_full_tt_100C_1v80/power_vcd.rpt"
    if f.exists(): l100 = parse_group_table(f)["Total"]["leakage"] * 1e6
    l37 = (leak * math.exp(math.log(l100 / leak) * (37 - 25) / (100 - 25))) if (leak and l100) else None
    items.append(dict(name=name + ("" if mode == "event" else "_" + mode), label=label, E=E, annotated=(mode + "_sdf" in d), parts=parts, leak=leak, leak100=l100, leak37=l37, dyn=E * RATE * 1e-3))
if not items: sys.exit("no 5 MHz measurements yet")
def sig2(v):
    t = f"{v:.2g}"; return t if ("." in t or v >= 10) else t + ".0"
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 3.0), gridspec_kw={"width_ratios": [1.15, 1]})
x = np.arange(len(items)); cols = {"Clock": "#7f9fbf", "Sequential": "#c0504d", "Combinational": "#e8c9a0", "Macro": "#777777"}
bottom = np.zeros(len(items))
for k in ("Clock", "Sequential", "Combinational", "Macro"):
    v = np.array([it["parts"][k] * 100 for it in items]); a1.bar(x, v, 0.7, bottom=bottom, color=cols[k], edgecolor="k", linewidth=0.3, label={"Clock": "clock network", "Sequential": "sequential cells", "Combinational": "combinational cells", "Macro": "memory block"}[k]); bottom += v
for xi, it in zip(x, items): a1.text(xi, 101, (f"{it['E']:.0f}" if it["E"] >= 100 else f"{it['E']:.2g}") + ("" if it["annotated"] else "*"), ha="center", va="bottom", fontsize=6)
a1.set_xticks(x); a1.set_xticklabels([it["label"] for it in items], rotation=35, ha="right", fontsize=6.5); a1.set_ylabel("share of power while decoding (%)\nnumbers: energy per bin in nJ"); a1.set_ylim(0, 112)
a1.legend(fontsize=6, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.42))
dyn = np.array([it["dyn"] for it in items]); lk = np.array([it["leak"] or 0 for it in items])
a2.bar(x, dyn, 0.7, color="#c0504d", edgecolor="k", linewidth=0.3, label="dynamic (E$_{bin}$ x 250/s)"); a2.bar(x, lk, 0.7, bottom=dyn, color="#dddddd", edgecolor="k", linewidth=0.3, label="leakage, 25 °C")
for xi, it in zip(x, items):
    if it["leak37"]: a2.plot([xi], [it["dyn"] + it["leak37"]], marker="_", color="k", ms=9, mew=1.2)
    a2.text(xi, max(it["dyn"] + (it["leak"] or 0), it["dyn"] + (it["leak37"] or 0)) * 1.12, sig2(it['dyn'] + (it['leak'] or 0)), ha="center", va="bottom", fontsize=6)
a2.plot([], [], marker="_", color="k", ls="", ms=9, mew=1.2, label="total with leakage at 37 °C")
a2.set_xticks(x); a2.set_xticklabels([it["label"] for it in items], rotation=35, ha="right", fontsize=6.5); a2.set_ylabel("average power at 250 bins/s (µW), clock stopped"); a2.set_yscale("log")
a2.legend(fontsize=6, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.42))
fig.tight_layout()
for out in (ROOT / "paper/figures", ROOT / "figures"):
    out.mkdir(exist_ok=True); fig.savefig(out / "power_breakdown5.pdf", bbox_inches="tight"); fig.savefig(out / "power_breakdown5.png", dpi=200, bbox_inches="tight")
with open(ROOT / "figures/power_breakdown5.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["design", "energy_per_bin_nJ", "annotated", "clock_share", "sequential_share", "combinational_share", "macro_share", "leakage_25C_uW", "leakage_100C_uW", "leakage_37C_uW", "p_avg_250Hz_uW"])
    for it in items: w.writerow([it["name"], it["E"], it["annotated"], it["parts"]["Clock"], it["parts"]["Sequential"], it["parts"]["Combinational"], it["parts"]["Macro"], it["leak"], it["leak100"], it["leak37"], it["dyn"] + (it["leak"] or 0)])
print("wrote", out / "power_breakdown5.pdf", len(items), "cores")
