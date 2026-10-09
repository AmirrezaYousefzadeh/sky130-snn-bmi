#!/usr/bin/env python3
"""Round 10: power breakdown of the Table 2 cores from the real-time runs (results/round10.json, sw/collect_round10.py).
Left: shares of the dynamic power (P_total - P_leakage, root-clock correction applied) by cell group - clock network, sequential
cells, combinational cells, memory block - of the same real-time run; the number above each bar is E_bin (nJ). Right: P_avg at
250 bins/s split into the dynamic part (P_total - P_leakage) and P_leakage, both as reported by OpenSTA for the real-time run.
Writes deliverables_round10/figures/power_breakdown5.{pdf,png,csv} (and figures/power_breakdown10.*); with --statecorr the variant
that includes the SRAM-macro state correction of the SRAM-core and SoC rows (suffix _statecorr). The left panel takes the groups of
the OpenSTA report; the root-clock correction is taken off the clock network."""
import json, sys, csv
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parent.parent
R = json.load(open(ROOT / "results/round10.json"))
STATECORR = "--statecorr" in sys.argv          # variant with the SRAM-macro state correction included (file suffix _statecorr)
ORDER = [("soc_tuned", "RISC-V SoC"), ("topg_dense", "SRAM seq., dense"), ("topg_event", "SRAM seq., event"), ("scmemg", "flip-flop mem."), ("lmem2g", "latch mem. 20-bit"), ("lmin2", "latch mem. 12-bit"),
         ("hwg", "hw 20-bit"), ("ming", "hw 16-bit"), ("m12", "hw 12-bit"), ("sp", "pruned 25 %"), ("min32g", "H=32, 16-bit"), ("g32p50", "H=32, 50 %"), ("fe", "front end")]
items = []
for key, label in ORDER:
    rs = [r for r in R["table2"] if r["key"] == key and r.get("role") == "table" and r.get("status") == "ok"]
    if not rs: continue
    r = rs[0]; g = r.get("groups_unc") or {}            # OpenSTA group table (clock network / sequential / combinational / macro)
    dyn = {k: (g.get(k, {}).get("internal", 0) + g.get(k, {}).get("switching", 0)) for k in ("Clock", "Sequential", "Combinational", "Macro")}
    dyn["Clock"] = max(dyn["Clock"] - (r.get("root_removed_uW") or 0), 0.0)        # root-clock correction: the removed power sits in the clock network
    E, pdyn = r["e_bin_nJ"], r["p_dyn_uW"]
    if STATECORR and r.get("macro_corr_uW"):                                          # SRAM22 macro state correction (see run log): added to the memory block
        dyn["Macro"] += r["macro_corr_uW"]; E = r["e_bin_mc_nJ"]; pdyn = r["p_dyn_mc_uW"]
    tot = sum(dyn.values()) or 1.0
    items.append(dict(key=key, label=label, E=E, dyn=pdyn, leak=r["p_leak_uW"], shares={k: v / tot for k, v in dyn.items()}, win=r.get("window_bins"), kind=r.get("run_kind")))
if not items: sys.exit("no round-10 runs collected yet")
def sig2(v): t = f"{v:.2g}"; return t if ("." in t or v >= 10) else t + ".0"
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 3.3), gridspec_kw={"width_ratios": [1.15, 1]})
x = np.arange(len(items)); cols = {"Clock": "#7f9fbf", "Sequential": "#c0504d", "Combinational": "#e8c9a0", "Macro": "#777777"}
bottom = np.zeros(len(items))
for k in ("Clock", "Sequential", "Combinational", "Macro"):
    v = np.array([it["shares"][k] * 100 for it in items]); a1.bar(x, v, 0.7, bottom=bottom, color=cols[k], edgecolor="k", linewidth=0.3, label={"Clock": "clock network", "Sequential": "sequential cells", "Combinational": "combinational cells", "Macro": "memory block"}[k]); bottom += v
for xi, it in zip(x, items): a1.text(xi, 101, (f"{it['E']:.0f}" if it["E"] >= 100 else sig2(it["E"])), ha="center", va="bottom", fontsize=6)
a1.set_xticks(x); a1.set_xticklabels([it["label"] for it in items], rotation=35, ha="right", fontsize=6.5); a1.set_ylabel("dynamic power share (%)"); a1.set_ylim(0, 112)
a1.legend(fontsize=6, frameon=False, loc="upper center", ncol=2, bbox_to_anchor=(0.5, -0.42))
dyn = np.array([it["dyn"] for it in items]); lk = np.array([it["leak"] for it in items])
a2.bar(x, dyn, 0.7, color="#c0504d", edgecolor="k", linewidth=0.3, label="dynamic ($P_{\\mathrm{total}} - P_{\\mathrm{leakage}}$)"); a2.bar(x, lk, 0.7, bottom=dyn, color="#dddddd", edgecolor="k", linewidth=0.3, label="leakage ($P_{\\mathrm{leakage}}$, 25 °C)")
for xi, it in zip(x, items): a2.text(xi, (it["dyn"] + it["leak"]) * 1.12, sig2(it["dyn"] + it["leak"]), ha="center", va="bottom", fontsize=6)
a2.set_xticks(x); a2.set_xticklabels([it["label"] for it in items], rotation=35, ha="right", fontsize=6.5); a2.set_ylabel("$P_{\\mathrm{avg}}$ at 250 bins/s (µW)"); a2.set_yscale("log")
a2.legend(fontsize=6, frameon=False, loc="upper center", ncol=1, bbox_to_anchor=(0.5, -0.42))
fig.tight_layout()
sfx = "_statecorr" if STATECORR else ""
outs = [ROOT / f"deliverables_round10/figures/power_breakdown5{sfx}", ROOT / f"figures/power_breakdown10{sfx}"]
for o in outs:
    o.parent.mkdir(parents=True, exist_ok=True); fig.savefig(str(o) + ".pdf"); fig.savefig(str(o) + ".png", dpi=200)
    with open(str(o) + ".csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["key", "label", "window_bins", "delay_model", "e_bin_nJ", "p_dyn_uW", "p_leak_uW", "share_clock", "share_sequential", "share_combinational", "share_macro"])
        for it in items: w.writerow([it["key"], it["label"], it["win"], it["kind"], f"{it['E']:.5g}", f"{it['dyn']:.5g}", f"{it['leak']:.5g}"] + [f"{it['shares'][k]:.4f}" for k in ("Clock", "Sequential", "Combinational", "Macro")])
print(f"wrote {outs[0]}.pdf ({len(items)} cores)")
