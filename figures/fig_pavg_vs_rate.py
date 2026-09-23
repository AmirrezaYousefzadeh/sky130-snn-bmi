#!/usr/bin/env python3
"""Round 5, figure F2: average decoder-core power against decode rate, per kit and flavour, clock stopped between bins:
P(f) = E_bin x f + P_leak, with the annotated E_bin where an annotated run exists (zero-delay for NanGate45; re-evaluated
supply corners use the zero-delay energy scaled by the glitch factor measured on the same netlist at its nominal supply)
and the total leakage of the idle run (25 C unless stated). Panel (a) bmi_snn_sp, panel (b) bmi_snn_min32.
Flavours: sky130 1.8 V and 1.28 V (the E14 netlist hardened with 1.28 V signoff, -40 C slow corner, the only 1.28 V liberty; the E5 re-evaluation of the 1.8 V netlist is the fallback), sky130 at the interpolated 37 C leakage
(dotted), GF180MCU 5 V and 1.8 V, IHP SG13G2, NanGate45, ASAP7 SRAM-Vt and RVT. Vertical dashed line and a marker on every
line at 250 bins/s. Reads results/pdks5.json (sw/collect_pdks5.py) and the 100 C idle re-evaluation of the sky130 cores.
Writes paper/figures/pavg_vs_rate.{pdf,png}, figures/pavg_vs_rate.{pdf,png} and figures/pavg_vs_rate.csv."""
import json, csv, sys, math
from pathlib import Path
import numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "sw")); from collect_results import parse_group_table
P = json.load(open(ROOT / "results/pdks5.json"))
C5 = json.load(open(ROOT / "results/corners5.json")) if (ROOT / "results/corners5.json").exists() else {}
RATE = 250.0
# kit key, legend label, colour (Okabe-Ito), low-supply corner to draw (None = nominal only)
KITS = [("sky130", "sky130, 1.8 V", "#D55E00", "ss_n40C_1v28", "sky130, 1.28 V (-40 °C)"), ("gf180", "GF180MCU, 5 V", "#E69F00", "tt_025C_1v80", "GF180MCU, 1.8 V"),
        ("ihp", "IHP SG13G2, 1.2 V", "#0072B2", None, None), ("nangate45", "NanGate45, 1.1 V (zero-delay)", "#999999", None, None),
        ("asap7sram", "ASAP7 SRAM-Vt, 0.7 V", "#009E73", None, None), ("asap7", "ASAP7 RVT, 0.7 V", "#56B4E9", None, None)]
CORES = [("sp", "(a) pruned 12-bit core, H = 64, 25 % synapses"), ("min32", "(b) hardwired 16-bit core, H = 32")]
rates = np.logspace(0, 4, 300)
plt.rcParams.update({"font.size": 8, "font.family": "sans-serif", "axes.spines.top": False, "axes.spines.right": False})
fig, axs = plt.subplots(1, 2, figsize=(6.4, 3.1), sharey=True)
rows = []
def curve(ax, e, leak, col, ls, lw, label, core, kit, flavour, V, T, kind):
    ax.plot(rates, e * rates * 1e-3 + leak, color=col, lw=lw, ls=ls, zorder=2)
    p250 = e * RATE * 1e-3 + leak; ax.plot([RATE], [p250], marker="o", ms=3.2, color=col, mec="k", mew=0.4, ls="", zorder=3)
    rows.append(dict(core=core, kit=kit, flavour=flavour, voltage_V=V, temperature_C=T, energy_per_bin_nJ=e, energy_kind=kind, leakage_uW=leak, p_avg_250Hz_uW=p250, linestyle=ls))
for ax, (core, title) in zip(axs, CORES):
    for kit, label, col, lowc, lowlabel in KITS:
        d = P.get(f"{kit}/{core}")
        if not d or not d.get("event") or not d.get("idle"): continue
        ann = d.get("event_sdf"); e_nom = (ann or d["event"])["energy_per_bin_nJ"]; kind = "annotated" if ann else "zero-delay"
        w5 = d.get("event_sdf_w5000")                                       # round 6 (E2): the 5,000-bin window, the same as Table 3
        if w5: e_nom = w5["energy_per_bin_nJ"]; kind = ("zero-delay" if w5.get("zero_delay") else "annotated") + ", 5,000 bins"
        glitch = (ann["energy_per_bin_nJ"] / d["event"]["energy_per_bin_nJ"]) if ann else 1.0
        lk = d["idle"]["leakage_uW"]; V = d.get("voltage"); T = d.get("temperature", 25)
        curve(ax, e_nom, lk, col, "-", 1.3, label, core, kit, "nominal", V, T, kind)
        if kit == "ihp":      # round 6 (E3): the IHP total leakage is dominated by the decap fill of the 20 % floorplan; show the logic-only floor too
            ll = (d.get("leak_split") or {}).get("leak_logic_uW")
            if ll: curve(ax, e_nom, ll, col, ":", 1.1, "IHP SG13G2, logic-cell leakage only", core, kit, "nominal, logic leakage only", V, T, kind)
            nd = d.get("leak_nodecap_uW")
            if nd: curve(ax, e_nom, nd, col, "-.", 1.1, "IHP SG13G2, fill without decap cells", core, kit, "nominal, decap-free fill", V, T, kind)
        if kit == "sky130":   # 37 C leakage, interpolated exponentially between the 25 C and 100 C idle evaluations
            f = ROOT / f"power/out_vcd_bmi_snn_{core}_5m_idle_full_tt_100C_1v80/power_vcd.rpt"
            if f.exists():
                l100 = parse_group_table(f)["Total"]["leakage"] * 1e6; l37 = lk * math.exp(math.log(l100 / lk) * (37 - 25) / (100 - 25))
                curve(ax, e_nom, l37, col, ":", 1.1, "sky130, 1.8 V, leakage at 37 °C", core, kit, "nominal, 37 C leakage", V, 37, kind)
        if lowc and lowc in (d.get("volt") or {}):
            v = d["volt"][lowc]
            lv = (C5.get(f"bmi_snn_{core}") or {}).get("lv") or {}
            if kit == "sky130" and lv.get("e_sdf_1v28") and lv.get("leak_1v28_uW") is not None:
                # E14: the core hardened with 1.28 V signoff, annotated run and idle run of that netlist at ss_n40C_1v28
                e_low, leak_low, kind_low, flav = lv["e_sdf_1v28"]["energy_per_bin_nJ"], lv["leak_1v28_uW"], "annotated (1.28 V netlist, E14)", "ss_n40C_1v28 netlist"
            else:   # the nominal netlist re-evaluated with the low-supply liberty (E5), zero-delay activity
                e_low, leak_low, kind_low, flav = v["energy_per_bin_nJ"] * glitch, v["leakage_uW"], f"zero-delay x glitch {glitch:.2f}", lowc
            curve(ax, e_low, leak_low, col, "--", 1.1, lowlabel, core, kit, flav, v["voltage"], v["temperature"], kind_low)
    ax.axvline(RATE, color="k", lw=0.6, ls="--"); ax.text(RATE * 1.15, 0.012, "250 bins/s", fontsize=6, ha="left")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(1, 1e4); ax.set_ylim(0.01, 1000); ax.set_xlabel("decode rate (bins/s)"); ax.set_title(title, fontsize=8, loc="left")
axs[0].set_ylabel("average core power (µW)")   # "clock stopped between bins" is in the caption (round 6)
seen = {r["kit"] + r["linestyle"] for r in rows}
handles = []
for kit, label, col, lowc, lowlabel in KITS:
    if kit + "-" in seen: handles.append(Line2D([], [], color=col, lw=1.3, label=label))
    if kit == "sky130" and kit + ":" in seen: handles.append(Line2D([], [], color=col, lw=1.1, ls=":", label="sky130, 1.8 V, leakage at 37 °C"))   # round 7: was added for every kit with a dotted line (duplicate)
    if kit + "--" in seen: handles.append(Line2D([], [], color=col, lw=1.1, ls="--", label=lowlabel))
    if kit == "ihp" and kit + ":" in seen: handles.append(Line2D([], [], color=col, lw=1.1, ls=":", label="IHP SG13G2, logic-cell leakage only"))
    if kit == "ihp" and kit + "-." in seen: handles.append(Line2D([], [], color=col, lw=1.1, ls="-.", label="IHP SG13G2, fill without decap cells"))
handles.append(Line2D([], [], marker="o", ms=3.2, color="0.4", mec="k", mew=0.4, ls="", label="value at 250 bins/s"))
fig.legend(handles=handles, fontsize=6.5, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.0), columnspacing=1.2, handlelength=2.2)
fig.tight_layout(rect=(0, 0.02, 1, 1))
for out in (ROOT / "paper/figures", ROOT / "figures"):
    out.mkdir(exist_ok=True); fig.savefig(out / "pavg_vs_rate.pdf", bbox_inches="tight"); fig.savefig(out / "pavg_vs_rate.png", dpi=200, bbox_inches="tight")
with open(ROOT / "figures/pavg_vs_rate.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("wrote", out / "pavg_vs_rate.pdf", len(rows), "curves")
