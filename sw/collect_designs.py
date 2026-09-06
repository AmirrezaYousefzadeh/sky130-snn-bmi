#!/usr/bin/env python3
"""Collect PPA + energy for all core variants into results/designs.json (and a Markdown table).

Naming convention of the measurement runs (see run_gls.sh TAG and run_vcd_power.sh):
  sim/build_<tag>/vvp.log, power/out_vcd_<tag>/power_vcd.rpt   with tag = <design>_md0_full | <design>_md1_full | <design>_idle_full
  (the original SRAM core keeps its legacy tags gls_md0_full / gls_md1_full / gls_idle2_full)
  optional SDF runs: <design>_md0_sdf, <design>_md1_sdf, <design>_idle_sdf
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_results import parse_group_table, parse_tb_summary, parse_metrics, parse_instance_report, RATE

ROOT = Path(__file__).resolve().parent.parent
DESIGNS = {
    "bmi_snn_top":   {"label": "SRAM macro, sequential (v1)", "tags": {"event": "gls_md0_full", "dense": "gls_md1_full", "idle": "gls_idle2_full"}, "tclk": 20.0, "macro": "u_wmem"},
    "bmi_snn_scmem": {"label": "std-cell register file, parallel", "tags": {"event": "bmi_snn_scmem_md0_full", "dense": "bmi_snn_scmem_md1_full", "idle": "bmi_snn_scmem_idle_full"}, "tclk": 20.0, "macro": None},
    "bmi_snn_hw":    {"label": "hardwired weights, parallel", "tags": {"event": "bmi_snn_hw_md0_full", "dense": "bmi_snn_hw_md1_full", "idle": "bmi_snn_hw_idle_full"}, "tclk": 20.0, "macro": None},
    "bmi_snn_min":   {"label": "hardwired, 16-bit state, no dense logic", "tags": {"event": "bmi_snn_min_md0_full", "dense": "bmi_snn_min_md1_full", "idle": "bmi_snn_min_idle_full"}, "tclk": 20.0, "macro": None},
    "bmi_snn_min32": {"label": "hardwired, 16-bit, H=32 (R2 0.572)", "tags": {"event": "bmi_snn_min32_md0_full", "dense": "bmi_snn_min32_md1_full", "idle": "bmi_snn_min32_idle_full"}, "tclk": 20.0, "macro": None},
    "bmi_snn_min16": {"label": "hardwired, 16-bit, H=16 (R2 0.555)", "tags": {"event": "bmi_snn_min16_md0_full", "dense": "bmi_snn_min16_md1_full", "idle": "bmi_snn_min16_idle_full"}, "tclk": 20.0, "macro": None},
}

def measured_cycles(log: Path) -> int | None:
    m = re.search(r"MEASURED: cycles_from_dump_start=(\d+)", log.read_text(errors="replace"))
    return int(m.group(1)) if m else None

def measured_active(log: Path) -> int | None:
    m = re.search(r"active_cycles_from_dump_start=(\d+)", log.read_text(errors="replace"))
    return int(m.group(1)) if m else None

def run_energy(tag: str, tclk: float, macro: str | None) -> dict | None:
    log = ROOT / f"sim/build_{tag}/vvp.log"; rpt = ROOT / f"power/out_vcd_{tag}/power_vcd.rpt"
    if not (log.exists() and rpt.exists()): return None
    tb = parse_tb_summary(log); g = parse_group_table(rpt)
    if "bins" not in tb or "Total" not in g: return None
    cyc = measured_cycles(log) or tb["cycles"]
    P = g["Total"]["total"]; T = cyc * tclk * 1e-9
    d = {"tag": tag, "tb": tb, "groups": g, "power_avg_uW": P * 1e6, "cycles_meas": cyc, "cycles_per_bin": cyc / tb["bins"],
         "energy_per_bin_nJ": P * T / tb["bins"] * 1e9, "latency_us": tb["avg_latency_cyc"] * tclk * 1e-3,
         "leakage_uW": g["Total"]["leakage"] * 1e6, "pass": tb.get("pass")}
    if macro:
        mr = ROOT / f"power/out_vcd_{tag}/power_vcd_{macro}.rpt"
        if mr.exists(): d["macro"] = parse_instance_report(mr, macro)
    return d

def run_idle(tag: str, tclk: float, P_dec: float | None) -> dict | None:
    log = ROOT / f"sim/build_{tag}/vvp.log"; rpt = ROOT / f"power/out_vcd_{tag}/power_vcd.rpt"
    if not (log.exists() and rpt.exists()): return None
    tb = parse_tb_summary(log); g = parse_group_table(rpt)
    if "bins" not in tb or "Total" not in g: return None
    cyc = measured_cycles(log) or tb["cycles"]
    act = measured_active(log); act = tb["active_cycles"] if act is None else act
    T = cyc * tclk * 1e-9; T_idle = (cyc - act) * tclk * 1e-9
    # remove the small active share using the measured active cycles of this run and the decoding power of the
    # back-to-back run (the design is >99 % idle here, so the residual error is well below 1 uW)
    E_active = (act * tclk * 1e-9) * (P_dec if P_dec else g["Total"]["total"])
    idle = (g["Total"]["total"] * T - E_active) / T_idle
    return {"tag": tag, "idle_power_uW": max(idle, g["Total"]["leakage"]) * 1e6, "leakage_uW": g["Total"]["leakage"] * 1e6, "groups": g,
            "idle_raw_uW": g["Total"]["total"] * 1e6, "active_share": act / cyc}

def main():
    out = {}
    for name, cfg in DESIGNS.items():
        d = {"label": cfg["label"], "tclk_ns": cfg["tclk"]}
        # PnR results: the primary run if it passed timing, else the lower-utilisation hedge run (<name>_lo)
        cands = (ROOT / f"synthesis/{name}/runs/{name}", ROOT / f"synthesis/{name}_lo/runs/{name}_lo2", ROOT / f"synthesis/{name}_lo/runs/{name}_lo")
        for rd in cands:
            sr = rd / "synthesis_results.txt"
            if sr.exists() and "RESULT: PASS" in sr.read_text() and (rd / "final/metrics.json").exists():
                d["pnr"] = parse_metrics(rd / "final/metrics.json"); d["pnr"]["run_dir"] = str(rd); d["pnr"]["timing_met"] = True; break
        if "pnr" not in d:   # no passing run: report the most recent routed run and flag it
            for rd in sorted([c for c in cands if (c / "final/metrics.json").exists()], key=lambda c: (c / "final/metrics.json").stat().st_mtime, reverse=True):
                d["pnr"] = parse_metrics(rd / "final/metrics.json"); d["pnr"]["run_dir"] = str(rd); d["pnr"]["timing_met"] = False; break
        for mode in ("event", "dense"):
            r = run_energy(cfg["tags"][mode], cfg["tclk"], cfg["macro"])
            if r: d[mode] = r
            rs = run_energy(f"{name}_md{0 if mode=='event' else 1}_sdf", cfg["tclk"], cfg["macro"])
            if rs: d[mode + "_sdf"] = rs
        P_dec = d["event"]["power_avg_uW"] * 1e-6 if "event" in d else None
        r = run_idle(cfg["tags"]["idle"], cfg["tclk"], P_dec)
        if r: d["idle"] = r
        for f_label, f_mhz in (("50MHz", 50.0), ("1MHz", 1.0)):
            if "event" in d and "idle" in d:
                # idle dynamic part scales with the always-on clock frequency; leakage does not
                idle_dyn = max(d["idle"]["idle_power_uW"] - d["idle"]["leakage_uW"], 0) * (f_mhz / (1e3 / cfg["tclk"]))
                d[f"avg_power_uW_250Hz_clk{f_label}"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"] + idle_dyn
        if "event" in d and "idle" in d:
            d["avg_power_uW_250Hz_clkstopped"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"]
        out[name] = d
    (ROOT / "results/designs.json").write_text(json.dumps(out, indent=1, default=float))
    # markdown table
    rows = [("design", *[out[n]["label"] for n in out])]
    def row(label, key):
        vals = []
        for n in out:
            v = key(out[n]) if out[n] else None
            vals.append("" if v is None else (f"{v:,.3g}" if isinstance(v, float) else str(v)))
        rows.append((label, *vals))
    row("area, cells + macro (mm²)", lambda d: d["pnr"]["instance_area_um2"] / 1e6 if "pnr" in d else None)
    row("std-cell area (mm²)", lambda d: d["pnr"]["stdcell_area_um2"] / 1e6 if "pnr" in d else None)
    row("std cells", lambda d: d["pnr"]["stdcells"] if "pnr" in d else None)
    row("setup slack @20 ns (ns)", lambda d: d["pnr"]["setup_ws_ns"] if "pnr" in d else None)
    row("cycles / bin, event", lambda d: d["event"]["cycles_per_bin"] if "event" in d else None)
    row("power while decoding, event (µW)", lambda d: d["event"]["power_avg_uW"] if "event" in d else None)
    row("energy / bin, event (nJ)", lambda d: d["event"]["energy_per_bin_nJ"] if "event" in d else None)
    row("energy / bin, event, SDF (nJ)", lambda d: d["event_sdf"]["energy_per_bin_nJ"] if "event_sdf" in d else None)
    row("energy / bin, dense (nJ)", lambda d: d["dense"]["energy_per_bin_nJ"] if "dense" in d else None)
    row("latency after tick (µs)", lambda d: d["event"]["latency_us"] if "event" in d else None)
    row("leakage (µW)", lambda d: d["idle"]["leakage_uW"] if "idle" in d else None)
    row("idle power, 50 MHz clock running (µW)", lambda d: d["idle"]["idle_power_uW"] if "idle" in d else None)
    row("avg power @250 bins/s, 50 MHz clock (µW)", lambda d: d.get("avg_power_uW_250Hz_clk50MHz"))
    row("avg power @250 bins/s, 1 MHz clock (µW)", lambda d: d.get("avg_power_uW_250Hz_clk1MHz"))
    row("avg power @250 bins/s, clock stopped (µW)", lambda d: d.get("avg_power_uW_250Hz_clkstopped"))
    md = "| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n" + "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
    (ROOT / "results/DESIGNS.md").write_text("# Core variants (sky130 TT 1.8 V 25 °C, per-pin OpenSTA power, 20 ns clock)\n\n" + md + "\n")
    print(md)
    write_latex(out)
    make_variant_figure(out)

SHORT = {"bmi_snn_top": "Seq", "bmi_snn_scmem": "Rf", "bmi_snn_hw": "Hw", "bmi_snn_min": "Min", "bmi_snn_min32": "MinH", "bmi_snn_min16": "MinS"}
COLS = ["bmi_snn_top", "bmi_snn_scmem", "bmi_snn_hw", "bmi_snn_min", "bmi_snn_min32", "bmi_snn_min16"]
HEAD = ["SRAM seq.", "reg.\\ file", "hardwired", "hw 16-bit", "hw 16-bit $H{=}32$", "hw 16-bit $H{=}16$"]

def _f(x, nd=3):
    if x is None: return "--"
    if abs(x) >= 1000: return f"{x:,.0f}"
    return f"{x:.{nd}g}"

def write_latex(out):
    """paper/numbers2.tex (macros per variant) and paper/designs_table.tex (the PPA table body)."""
    L = []
    def mac(n, v, nd=3): L.append(f"\\newcommand{{\\{n}}}{{{_f(v, nd)}}}")
    for name in COLS:
        d = out.get(name, {}); sh = SHORT[name]; p = d.get("pnr", {})
        mac(f"area{sh}", p["instance_area_um2"] / 1e6 if p else None); mac(f"cells{sh}", p.get("stdcells") if p else None, 4)
        mac(f"slack{sh}", p.get("setup_ws_ns") if p else None, 2)
        e = d.get("event", {}); mac(f"cyc{sh}", e.get("cycles_per_bin"), 3); mac(f"pdec{sh}", e.get("power_avg_uW"), 3)
        mac(f"e{sh}", e.get("energy_per_bin_nJ"), 3); mac(f"lat{sh}", e.get("latency_us"), 3)
        mac(f"eSdf{sh}", d.get("event_sdf", {}).get("energy_per_bin_nJ"), 3)
        mac(f"eDense{sh}", d.get("dense", {}).get("energy_per_bin_nJ"), 3)
        i = d.get("idle", {}); mac(f"leak{sh}", i.get("leakage_uW"), 3); mac(f"idle{sh}", i.get("idle_power_uW"), 3)
        mac(f"pavgFifty{sh}", d.get("avg_power_uW_250Hz_clk50MHz"), 3); mac(f"pavgOne{sh}", d.get("avg_power_uW_250Hz_clk1MHz"), 3)
        mac(f"pavgStop{sh}", d.get("avg_power_uW_250Hz_clkstopped"), 3)
    # ratios relative to the sequential SRAM core
    e0 = out.get("bmi_snn_top", {}).get("event", {}).get("energy_per_bin_nJ")
    for name in COLS[1:]:
        e1 = out.get(name, {}).get("event", {}).get("energy_per_bin_nJ")
        mac(f"gain{SHORT[name]}", (e0 / e1) if (e0 and e1) else None, 3)
    for name in COLS:
        d = out.get(name, {})
        ef, es = d.get("event", {}).get("energy_per_bin_nJ"), d.get("event_sdf", {}).get("energy_per_bin_nJ")
        mac(f"sdfRatio{SHORT[name]}", (es / ef) if (ef and es) else None, 3)
    # convenience ratios (avoid \fpeval on possibly undefined macros)
    def _area(n): return out.get(n, {}).get("pnr", {}).get("instance_area_um2")
    def _leak(n): return out.get(n, {}).get("idle", {}).get("leakage_uW")
    a0, a1 = _area("bmi_snn_top"), _area("bmi_snn_scmem"); mac("areaRatioRf", (a1 / a0) if (a0 and a1) else None, 2)
    l0, l1 = _leak("bmi_snn_top"), _leak("bmi_snn_scmem"); mac("leakRatioRf", (l1 / l0) if (l0 and l1) else None, 2)
    try:
        R1 = json.load(open(ROOT / "results/results.json")); ecpu = R1["riscv"]["energy_per_bin_nJ_active"]
    except Exception: ecpu = None
    em = out.get("bmi_snn_min32", {}).get("event", {}).get("energy_per_bin_nJ")
    mac("gainCpuMinH", (ecpu / em) if (ecpu and em) else None, 3)
    # placeholders for anything not defined
    ALL = [f"{k}{sh}" for sh in SHORT.values() for k in ("area","cells","slack","cyc","pdec","e","lat","eSdf","eDense","leak","idle","pavgFifty","pavgOne","pavgStop","sdfRatio")]
    ALL += [f"gain{sh}" for sh in list(SHORT.values())[1:]] + ["areaRatioRf", "leakRatioRf", "gainCpuMinH"]
    defined = {l.split("{")[1].split("}")[0].lstrip("\\") for l in L}
    for n in ALL:
        if n not in defined: L.append(f"\\newcommand{{\\{n}}}{{\\textcolor{{red}}{{?}}}}")
    (ROOT / "paper/numbers2.tex").write_text("% auto-generated by sw/collect_designs.py\n" + "\n".join(L) + "\n")
    rows = [("Weights", "SRAM22 macro", "flip-flops", "constants", "constants", "constants", "constants"),
            ("Lanes / cycles per row", "4 / 16", "64 / 1", "64 / 1", "64 / 1", "32 / 1", "16 / 1"),
            ("Membrane / output bits", "20 / 24", "20 / 24", "20 / 24", "16 / 16", "16 / 16", "16 / 16"),
            ("Dense-mode logic", "yes", "yes", "yes", "no", "no", "no"),
            ("Test $\\Rsq$ (mean)", "0.583", "0.583", "0.583", "0.583", "0.572", "0.555")]
    def r(label, key, nd=3):
        rows.append((label, *[_f(key(out.get(n, {})), nd) for n in COLS]))
    g = lambda d, *ks: (lambda x: x)(_get(d, ks))
    r("Area, cells + macro (mm$^2$)", lambda d: d["pnr"]["instance_area_um2"] / 1e6 if "pnr" in d else None)
    r("Standard cells", lambda d: d["pnr"]["stdcells"] if "pnr" in d else None, 4)
    r("Setup slack at 20\\,ns (ns)", lambda d: d["pnr"]["setup_ws_ns"] if "pnr" in d else None, 2)
    r("Active cycles per bin", lambda d: d["event"]["cycles_per_bin"] if "event" in d else None)
    r("Latency after tick (\\si{\\micro\\second})", lambda d: d["event"]["latency_us"] if "event" in d else None)
    r("Power while decoding (\\si{\\micro\\watt})", lambda d: d["event"]["power_avg_uW"] if "event" in d else None)
    r("\\textbf{Energy per bin, functional (nJ)}", lambda d: d["event"]["energy_per_bin_nJ"] if "event" in d else None)
    r("Energy per bin, SDF (nJ)", lambda d: d["event_sdf"]["energy_per_bin_nJ"] if "event_sdf" in d else None)
    r("Energy per bin, dense mode (nJ)", lambda d: d["dense"]["energy_per_bin_nJ"] if "dense" in d else None)
    r("Leakage (\\si{\\micro\\watt})", lambda d: d["idle"]["leakage_uW"] if "idle" in d else None)
    r("Idle, 50\\,MHz clock running (\\si{\\micro\\watt})", lambda d: d["idle"]["idle_power_uW"] if "idle" in d else None)
    r("$P_{\\mathrm{avg}}$ 250\\,bins/s, 50\\,MHz clock (\\si{\\micro\\watt})", lambda d: d.get("avg_power_uW_250Hz_clk50MHz"))
    r("$P_{\\mathrm{avg}}$ 250\\,bins/s, 1\\,MHz clock (\\si{\\micro\\watt})", lambda d: d.get("avg_power_uW_250Hz_clk1MHz"))
    r("\\textbf{$P_{\\mathrm{avg}}$ 250\\,bins/s, clock stopped (\\si{\\micro\\watt})}", lambda d: d.get("avg_power_uW_250Hz_clkstopped"))
    body = " & ".join(["", *HEAD]) + " \\\\\n\\midrule\n" + "\n".join(" & ".join(rw) + " \\\\" for rw in rows)
    (ROOT / "paper/designs_table.tex").write_text("\\begin{tabular}{lrrrrrr}\n\\toprule\n" + body + "\n\\bottomrule\n\\end{tabular}%\n")

def _get(d, ks):
    for k in ks:
        d = d.get(k, {}) if isinstance(d, dict) else {}
    return d if d != {} else None

def make_variant_figure(out):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    names = [n for n in COLS if n in out and "event" in out[n]]
    if len(names) < 2: return
    labels = {"bmi_snn_top": "SRAM\nsequential", "bmi_snn_scmem": "register\nfile", "bmi_snn_hw": "hard-\nwired", "bmi_snn_min": "hardwired\n16-bit", "bmi_snn_min32": "hardwired\n16-bit H=32", "bmi_snn_min16": "hardwired\n16-bit H=16"}
    fig, axs = plt.subplots(1, 3, figsize=(7.6, 2.6))
    x = np.arange(len(names))
    e = [out[n]["event"]["energy_per_bin_nJ"] for n in names]
    es = [out[n].get("event_sdf", {}).get("energy_per_bin_nJ", np.nan) for n in names]
    axs[0].bar(x - 0.2, e, 0.4, color="#c0504d", label="functional GLS"); axs[0].bar(x + 0.2, es, 0.4, color="#e8a09e", label="SDF GLS (glitches)")
    axs[0].set_ylabel("energy per 4 ms bin (nJ)"); axs[0].set_yscale("log"); axs[0].set_ylim(top=max(e) * 6)
    axs[0].legend(fontsize=6.5, frameon=False, loc="upper right")
    for i, v in enumerate(e): axs[0].text(x[i] - 0.2, v * 1.15, f"{v:.3g}", ha="center", fontsize=6.5)
    a = [out[n]["pnr"]["instance_area_um2"] / 1e6 if "pnr" in out[n] else np.nan for n in names]
    axs[1].bar(x, a, 0.55, color="#7f9fbf"); axs[1].set_ylabel("instance area (mm²)"); axs[1].set_ylim(top=np.nanmax(a) * 1.15)
    for i, v in enumerate(a):
        if np.isfinite(v): axs[1].text(x[i], v * 1.03, f"{v:.2f}", ha="center", fontsize=6.5)
    lk = [out[n]["idle"]["leakage_uW"] if "idle" in out[n] else np.nan for n in names]
    pa = [out[n].get("avg_power_uW_250Hz_clkstopped", np.nan) for n in names]
    axs[2].bar(x - 0.2, pa, 0.4, color="#5b9b6b", label="avg. power @250 bins/s, clock stopped")
    axs[2].bar(x + 0.2, lk, 0.4, color="#b8d8c0", label="of which leakage")
    axs[2].set_ylabel("µW"); axs[2].set_yscale("log"); axs[2].set_ylim(top=np.nanmax(pa) * 8)
    axs[2].legend(fontsize=6.5, frameon=False, loc="upper right")
    for ax in axs: ax.set_xticks(x); ax.set_xticklabels([labels[n] for n in names], fontsize=6.5)
    fig.tight_layout(); fig.savefig(ROOT / "paper/figures/variants.pdf"); fig.savefig(ROOT / "paper/figures/variants.png", dpi=200)

if __name__ == "__main__":
    main()
