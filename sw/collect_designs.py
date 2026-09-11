#!/usr/bin/env python3
"""Collect PPA + energy for all core variants into results/designs.json, results/DESIGNS.md, paper/numbers2.tex,
paper/designs_table.tex and paper/figures/variants.pdf.

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
SESS = ["indy_20160622_01", "indy_20160630_01", "indy_20170131_02"]
# design: label, short macro suffix, table columns (weights, lanes/cycles per row, bits, dense logic), accuracy source
#   r2: ("vbits", tag, key) -> results/explore/vbits_<tag>.json [key]["mean"]; ("eval", tag) -> mean of eval_int.json test_r2_int
D = lambda label, sh, weights, lanes, bits, dense, r2, fam, macro=None: dict(label=label, sh=sh, weights=weights, lanes=lanes, bits=bits, dense=dense, r2=r2, fam=fam, macro=macro)
DESIGNS = {
    "bmi_snn_top":   D("SRAM macro, sequential (v1)",                 "Seq",   "SRAM22 macro", "4 / 16", "20 / 24", "yes", ("vbits", "H64_th256_k44_drop", "v20_o24"), "seq", "u_wmem"),
    "bmi_snn_topg":  D("SRAM sequential, gated membrane groups",      "SeqG",  "SRAM22 macro", "4 / 16", "20 / 24", "yes", ("vbits", "H64_th256_k44_drop", "v20_o24"), "seq", "u_wmem"),
    "bmi_snn_scmem": D("std-cell register file (flip-flops), parallel", "Rf",  "flip-flops",   "64 / 1", "20 / 24", "yes", ("vbits", "H64_th256_k44_drop", "v20_o24"), "prog"),
    "bmi_snn_lmem":  D("std-cell latch memory, parallel",             "Lm",    "latches",      "64 / 1", "20 / 24", "yes", ("vbits", "H64_th256_k44_drop", "v20_o24"), "prog"),
    "bmi_snn_lmin":  D("latch memory, gated datapath, 12-bit",        "LmMin", "latches",      "64 / 1", "12 / 14", "no",  ("vbits", "H64_th256_k44_drop", "v12_o14"), "prog"),
    "bmi_snn_lmem2": D("latch memory, pipelined W2 read",              "LmP",   "latches",      "64 / 1", "20 / 24", "yes", ("vbits", "H64_th256_k44_drop", "v20_o24"), "prog"),
    "bmi_snn_lmin2": D("latch memory, gated, 12-bit, pipelined W2 read", "LmMinP", "latches",   "64 / 1", "12 / 14", "no",  ("vbits", "H64_th256_k44_drop", "v12_o14"), "prog"),
    "bmi_snn_hw":    D("hardwired weights, parallel",                 "Hw",    "constants",    "64 / 1", "20 / 24", "yes", ("vbits", "H64_th256_k44_drop", "v20_o24"), "hw"),
    "bmi_snn_min":   D("hardwired, 16-bit state, no dense logic",     "Min",   "constants",    "64 / 1", "16 / 16", "no",  ("vbits", "H64_th256_k44_drop", "v16_o16"), "hw"),
    "bmi_snn_ming":  D("hardwired 16-bit, gated datapath",            "MinG",  "constants",    "64 / 1", "16 / 16", "no",  ("vbits", "H64_th256_k44_drop", "v16_o16"), "hw"),
    "bmi_snn_m12":   D("hardwired 12-bit, gated datapath",            "MinT",  "constants",    "64 / 1", "12 / 14", "no",  ("vbits", "H64_th256_k44_drop", "v12_o14"), "hw"),
    "bmi_snn_sp":    D("hardwired 12-bit, gated, weights pruned to 25 %", "Sp", "constants (25 %)", "64 / 1", "12 / 14", "no", ("vbits", "H64_th256_k44_drop_p0.25", "v12_o14"), "hw"),
    "bmi_snn_sp8":   D("hardwired 12-bit, gated, weights pruned to 12.5 %", "SpE", "constants (12.5 %)", "64 / 1", "12 / 14", "no", ("vbits", "H64_th256_k44_drop_p0.125", "v12_o14"), "hw"),
    "bmi_snn_min32": D("hardwired, 16-bit, H=32",                    "MinH",  "constants",    "32 / 1", "16 / 16", "no",  ("eval", "H32_th256_k44_drop"), "hw"),
    "bmi_snn_min16": D("hardwired, 16-bit, H=16",                    "MinS",  "constants",    "16 / 1", "16 / 16", "no",  ("eval", "H16_th256_k44_drop"), "hw"),
}
LEGACY_TAGS = {"bmi_snn_top": {"event": "gls_md0_full", "dense": "gls_md1_full", "idle": "gls_idle2_full"}}
TCLK = 20.0

def r2_of(spec):
    try:
        if spec[0] == "vbits":
            return json.load(open(ROOT / "results/explore" / f"vbits_{spec[1]}.json"))[spec[2]]["mean"]
        vals = [json.load(open(ROOT / "results/models" / f"{s}_{spec[1]}" / "eval_int.json"))["test_r2_int"] for s in SESS]
        return float(np.mean(vals))
    except Exception:
        return None

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

def collect():
    out = {}
    for name, cfg in DESIGNS.items():
        d = {"label": cfg["label"], "tclk_ns": TCLK, "r2": r2_of(cfg["r2"]), "family": cfg["fam"],
             "weights": cfg["weights"], "lanes": cfg["lanes"], "bits": cfg["bits"], "dense_logic": cfg["dense"]}
        # PnR results: the primary run if it passed timing, else the lower-utilisation hedge run (<name>_lo)
        cands = (ROOT / f"synthesis/{name}/runs/{name}", ROOT / f"synthesis/{name}_lo/runs/{name}_lo2", ROOT / f"synthesis/{name}_lo/runs/{name}_lo")
        for rd in cands:
            sr = rd / "synthesis_results.txt"
            if sr.exists() and "RESULT: PASS" in sr.read_text() and (rd / "final/metrics.json").exists():
                d["pnr"] = parse_metrics(rd / "final/metrics.json"); d["pnr"]["run_dir"] = str(rd); d["pnr"]["timing_met"] = True; break
        if "pnr" not in d:   # no passing run: report the most recent routed run and flag it
            for rd in sorted([c for c in cands if (c / "final/metrics.json").exists()], key=lambda c: (c / "final/metrics.json").stat().st_mtime, reverse=True):
                d["pnr"] = parse_metrics(rd / "final/metrics.json"); d["pnr"]["run_dir"] = str(rd); d["pnr"]["timing_met"] = False; break
        tags = LEGACY_TAGS.get(name, {"event": f"{name}_md0_full", "dense": f"{name}_md1_full", "idle": f"{name}_idle_full"})
        for mode in ("event", "dense"):
            r = run_energy(tags[mode], TCLK, cfg["macro"])
            if r: d[mode] = r
            rs = run_energy(f"{name}_md{0 if mode=='event' else 1}_sdf", TCLK, cfg["macro"])
            if rs: d[mode + "_sdf"] = rs
        r200 = run_energy(f"{name}_md0_f200", TCLK, cfg["macro"])            # E1: functional run on the 200-bin SDF window
        if r200: d["event_f200"] = r200
        for s_ in SESS:                                                      # E9: other sessions' streams (energy transfer)
            rx = run_energy(f"{name}_md0_x{s_[5:]}", TCLK, cfg["macro"])
            if rx: d[f"event_x{s_[5:]}"] = rx
        P_dec = d["event"]["power_avg_uW"] * 1e-6 if "event" in d else None
        r = run_idle(tags["idle"], TCLK, P_dec)
        if r is None: r = run_idle(f"{name}_idle_sdf", TCLK, P_dec)
        if r: d["idle"] = r
        for f_label, f_mhz in (("50MHz", 50.0), ("1MHz", 1.0)):
            if "event" in d and "idle" in d:
                # idle dynamic part scales with the always-on clock frequency; leakage does not
                idle_dyn = max(d["idle"]["idle_power_uW"] - d["idle"]["leakage_uW"], 0) * (f_mhz / (1e3 / TCLK))
                d[f"avg_power_uW_250Hz_clk{f_label}"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"] + idle_dyn
        if "event" in d and "idle" in d:
            d["avg_power_uW_250Hz_clkstopped"] = d["event"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"]
            if "event_sdf" in d:
                d["avg_power_uW_250Hz_clkstopped_sdf"] = d["event_sdf"]["energy_per_bin_nJ"] * RATE * 1e-3 + d["idle"]["leakage_uW"]
        out[name] = d
    return out

def _f(x, nd=3):
    if x is None: return "--"
    if isinstance(x, str): return x
    if abs(x) >= 1000: return f"{x:,.0f}"
    return f"{x:.{nd}g}"

ROWS = [  # (label, key(d), digits)
    ("area, cells + macro (mm²)", lambda d: d["pnr"]["instance_area_um2"] / 1e6 if "pnr" in d else None, 3),
    ("std-cell area (mm²)", lambda d: d["pnr"]["stdcell_area_um2"] / 1e6 if "pnr" in d else None, 3),
    ("std cells", lambda d: d["pnr"]["stdcells"] if "pnr" in d else None, 4),
    ("setup slack @20 ns (ns)", lambda d: d["pnr"]["setup_ws_ns"] if "pnr" in d else None, 2),
    ("timing met at all corners", lambda d: ("yes" if d["pnr"]["timing_met"] else "no") if "pnr" in d else None, 3),
    ("test R² (mean of 3 sessions)", lambda d: d.get("r2"), 3),
    ("cycles / bin, event", lambda d: d["event"]["cycles_per_bin"] if "event" in d else None, 3),
    ("power while decoding, event (µW)", lambda d: d["event"]["power_avg_uW"] if "event" in d else None, 3),
    ("energy / bin, event (nJ)", lambda d: d["event"]["energy_per_bin_nJ"] if "event" in d else None, 3),
    ("energy / bin, event, SDF (nJ)", lambda d: d["event_sdf"]["energy_per_bin_nJ"] if "event_sdf" in d else None, 3),
    ("energy / bin, dense (nJ)", lambda d: d["dense"]["energy_per_bin_nJ"] if "dense" in d else None, 3),
    ("latency after tick (µs)", lambda d: d["event"]["latency_us"] if "event" in d else None, 3),
    ("leakage (µW)", lambda d: d["idle"]["leakage_uW"] if "idle" in d else None, 3),
    ("idle power, 50 MHz clock running (µW)", lambda d: d["idle"]["idle_power_uW"] if "idle" in d else None, 3),
    ("avg power @250 bins/s, 50 MHz clock (µW)", lambda d: d.get("avg_power_uW_250Hz_clk50MHz"), 3),
    ("avg power @250 bins/s, 1 MHz clock (µW)", lambda d: d.get("avg_power_uW_250Hz_clk1MHz"), 3),
    ("avg power @250 bins/s, clock stopped (µW)", lambda d: d.get("avg_power_uW_250Hz_clkstopped"), 3),
]

def write_markdown(out):
    names = [n for n in out if "pnr" in out[n] or "event" in out[n]]
    rows = [("design", *[out[n]["label"] for n in names])]
    for label, key, nd in ROWS:
        rows.append((label, *[_f(key(out[n]), nd) for n in names]))
    md = "| " + " | ".join(rows[0]) + " |\n|" + "---|" * len(rows[0]) + "\n" + "\n".join("| " + " | ".join(r) + " |" for r in rows[1:])
    (ROOT / "results/DESIGNS.md").write_text("# Core variants (sky130 TT 1.8 V 25 °C, per-pin OpenSTA power, 20 ns clock)\n\n" + md + "\n")
    print(md)

def write_latex(out):
    """paper/numbers2.tex (macros per variant) and paper/designs_table.tex (designs as rows)."""
    L = []
    def mac(n, v, nd=3): L.append(f"\\newcommand{{\\{n}}}{{{_f(v, nd)}}}")
    KEYS = ("area", "cells", "slack", "cyc", "pdec", "e", "lat", "eSdf", "eDense", "leak", "idle", "pavgFifty", "pavgOne", "pavgStop", "pavgStopSdf", "sdfRatio", "sdfRatioMixed", "rsq",
            "evWin", "evWinSdf", "evWinF", "nbevWin", "nbevWinSdf", "nbevWinF")
    for name, cfg in DESIGNS.items():
        d = out.get(name, {}); sh = cfg["sh"]; p = d.get("pnr", {})
        mac(f"area{sh}", p["instance_area_um2"] / 1e6 if p else None); mac(f"cells{sh}", p.get("stdcells") if p else None, 4)
        mac(f"slack{sh}", p.get("setup_ws_ns") if p else None, 2)
        e = d.get("event", {}); mac(f"cyc{sh}", e.get("cycles_per_bin"), 3); mac(f"pdec{sh}", e.get("power_avg_uW"), 3)
        mac(f"e{sh}", e.get("energy_per_bin_nJ"), 3); mac(f"lat{sh}", e.get("latency_us"), 3)
        es = d.get("event_sdf", {}).get("energy_per_bin_nJ"); mac(f"eSdf{sh}", es, 3)
        mac(f"eDense{sh}", d.get("dense", {}).get("energy_per_bin_nJ"), 3)
        i = d.get("idle", {}); mac(f"leak{sh}", i.get("leakage_uW"), 3); mac(f"idle{sh}", i.get("idle_power_uW"), 3)
        mac(f"pavgFifty{sh}", d.get("avg_power_uW_250Hz_clk50MHz"), 3); mac(f"pavgOne{sh}", d.get("avg_power_uW_250Hz_clk1MHz"), 3)
        mac(f"pavgStop{sh}", d.get("avg_power_uW_250Hz_clkstopped"), 3); mac(f"pavgStopSdf{sh}", d.get("avg_power_uW_250Hz_clkstopped_sdf"), 3)
        ef = e.get("energy_per_bin_nJ")
        # glitch factor from the same simulation window: an SDF run of N bins is compared with a functional run of N bins
        # (the <design>_md0_f200 runs of the referee experiment E1 where the SDF window is shorter than the 500-bin functional one)
        ef_same = None
        if es:
            if d.get("event_sdf", {}).get("tb", {}).get("bins") == e.get("tb", {}).get("bins"): ef_same = ef
            elif "event_f200" in d and d["event_f200"]["tb"]["bins"] == d["event_sdf"]["tb"]["bins"]: ef_same = d["event_f200"]["energy_per_bin_nJ"]
        mac(f"sdfRatio{sh}", (es / ef_same) if (ef_same and es) else None, 3)
        mac(f"sdfRatioMixed{sh}", (es / ef) if (ef and es) else None, 3)     # SDF window against the full functional window
        for key, suf in (("event", "evWin"), ("event_sdf", "evWinSdf"), ("event_f200", "evWinF")):
            tb = d.get(key, {}).get("tb", {})
            mac(f"{suf}{sh}", (tb["events"] / tb["bins"]) if tb.get("bins") else None, 3)
            mac(f"bins{suf[5:] or 'Func'}{sh}" if False else f"nb{suf}{sh}", tb.get("bins"), 4)
        mac(f"rsq{sh}", d.get("r2"), 3)
    e0 = out.get("bmi_snn_top", {}).get("event", {}).get("energy_per_bin_nJ")
    for name, cfg in DESIGNS.items():
        if name == "bmi_snn_top": continue
        e1 = out.get(name, {}).get("event", {}).get("energy_per_bin_nJ")
        mac(f"gain{cfg['sh']}", (e0 / e1) if (e0 and e1) else None, 3)
    def _area(n): return out.get(n, {}).get("pnr", {}).get("instance_area_um2")
    def _leak(n): return out.get(n, {}).get("idle", {}).get("leakage_uW")
    def _e(n, k="event"): return out.get(n, {}).get(k, {}).get("energy_per_bin_nJ")
    def ratio(a, b): return (a / b) if (a and b) else None
    mac("areaRatioRf", ratio(_area("bmi_snn_scmem"), _area("bmi_snn_top")), 2)
    mac("leakRatioRf", ratio(_leak("bmi_snn_scmem"), _leak("bmi_snn_top")), 2)
    mac("areaRatioLmRf", ratio(_area("bmi_snn_lmem"), _area("bmi_snn_scmem")), 2)
    mac("leakRatioLmRf", ratio(_leak("bmi_snn_lmem"), _leak("bmi_snn_scmem")), 2)
    mac("gainGate", ratio(_e("bmi_snn_min"), _e("bmi_snn_ming")), 2)
    mac("gainTwelve", ratio(_e("bmi_snn_ming"), _e("bmi_snn_m12")), 3)
    mac("gainSpVsTwelve", ratio(_e("bmi_snn_m12"), _e("bmi_snn_sp")), 2)
    mac("gainSpEVsTwelve", ratio(_e("bmi_snn_m12"), _e("bmi_snn_sp8")), 2)
    mac("gainMinSp", ratio(_e("bmi_snn_min"), _e("bmi_snn_sp")), 2)
    mac("gainMinSpE", ratio(_e("bmi_snn_min"), _e("bmi_snn_sp8")), 2)
    try:
        R1 = json.load(open(ROOT / "results/results.json")); ecpu = R1["riscv"]["energy_per_bin_nJ_active"]
    except Exception: ecpu = None
    mac("gainCpuMinH", ratio(ecpu, _e("bmi_snn_min32")), 3)
    best = min((n for n in DESIGNS if _e(n) and (out[n].get("r2") or 0) >= 0.57), key=lambda n: _e(n), default=None)
    mac("gainCpuBest", ratio(ecpu, _e(best)) if best else None, 3)
    L.append(f"\\newcommand{{\\bestCore}}{{{DESIGNS[best]['label'].replace('%', chr(92)+'%') if best else '?'}}}")
    ALL = [f"{k}{cfg['sh']}" for cfg in DESIGNS.values() for k in KEYS]
    ALL += [f"gain{cfg['sh']}" for n, cfg in DESIGNS.items() if n != "bmi_snn_top"]
    ALL += ["areaRatioRf", "leakRatioRf", "areaRatioLmRf", "leakRatioLmRf", "gainGate", "gainTwelve", "gainSpVsTwelve", "gainSpEVsTwelve", "gainMinSp", "gainMinSpE", "gainCpuMinH", "gainCpuBest"]
    defined = {l.split("{")[1].split("}")[0].lstrip("\\") for l in L}
    for n in ALL:
        if n not in defined: L.append(f"\\newcommand{{\\{n}}}{{\\textcolor{{red}}{{?}}}}")
    (ROOT / "paper/numbers2.tex").write_text("% auto-generated by sw/collect_designs.py\n" + "\n".join(L) + "\n")
    # ---- table: designs as rows
    hdr = ["Core", "Weights", "Lanes / cyc.", "Bits", "$\\Rsq$", "Area", "Cells", "Slack", "Cyc.", "$E_{\\mathrm{bin}}$", "$E_{\\mathrm{bin}}$ SDF", "Leak.", "$P_{\\mathrm{avg}}$"]
    units = ["", "", "per row", "$V$ / $o$", "", "mm$^2$", "", "ns", "/bin", "nJ", "nJ", "\\si{\\micro\\watt}", "\\si{\\micro\\watt}"]
    TL = {"bmi_snn_top": "SRAM, sequential (v1)", "bmi_snn_topg": "SRAM, seq., gated membrane groups", "bmi_snn_scmem": "flip-flop register file",
          "bmi_snn_lmem": "latch memory", "bmi_snn_lmin": "latch memory, gated, 12-bit", "bmi_snn_hw": "hardwired 20-bit",
          "bmi_snn_lmem2": "latch memory, pipelined $W_2$ read", "bmi_snn_lmin2": "latch memory, gated, 12-bit, pipelined $W_2$ read",
          "bmi_snn_min": "hardwired 16-bit", "bmi_snn_ming": "hardwired 16-bit, gated", "bmi_snn_m12": "hardwired 12-bit, gated",
          "bmi_snn_sp": "hardwired 12-bit, gated, 25\\,\\% synapses", "bmi_snn_sp8": "hardwired 12-bit, gated, 12.5\\,\\% synapses",
          "bmi_snn_min32": "hardwired 16-bit, $H{=}32$", "bmi_snn_min16": "hardwired 16-bit, $H{=}16$"}
    rows = []
    for name, cfg in DESIGNS.items():
        d = out.get(name, {})
        if "pnr" not in d and "event" not in d: continue
        p = d.get("pnr", {}); e = d.get("event", {})
        setup = p.get("setup_ws_ns") if p else None; hold = p.get("hold_ws_ns") if p else None
        flags = ("$^{\\dagger}$" if (setup is not None and setup < 0) else "") + ("$^{\\ddagger}$" if (hold is not None and hold < 0) else "")
        slack = (_f(setup, 2) + flags) if p else "--"
        rows.append([TL[name], cfg["weights"].replace("%", "\\%"), cfg["lanes"], cfg["bits"], _f(d.get("r2"), 3), _f(p["instance_area_um2"] / 1e6 if p else None),
                     _f(p.get("stdcells") if p else None, 4), slack, _f(e.get("cycles_per_bin"), 3), _f(e.get("energy_per_bin_nJ")),
                     _f(d.get("event_sdf", {}).get("energy_per_bin_nJ")), _f(d.get("idle", {}).get("leakage_uW")), _f(d.get("avg_power_uW_250Hz_clkstopped"))])
    body = " & ".join(hdr) + " \\\\\n" + " & ".join(units) + " \\\\\n\\midrule\n" + "\n".join(" & ".join(r) + " \\\\" for r in rows)
    (ROOT / "paper/designs_table.tex").write_text("\\begin{tabular}{@{}lllcc rrrr rrrr@{}}\n\\toprule\n" + body + "\n\\bottomrule\n\\end{tabular}%\n")

def make_variant_figure(out):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    names = [n for n in DESIGNS if n in out and "event" in out[n]]
    if len(names) < 2: return
    col = {"seq": "#c0504d", "prog": "#7f6fbf", "hw": "#2e7d5b"}
    mk = {"seq": "s", "prog": "D", "hw": "o"}
    short = {"bmi_snn_top": "SRAM v1", "bmi_snn_topg": "SRAM gated", "bmi_snn_scmem": "flip-flop RF", "bmi_snn_lmem": "latch mem.", "bmi_snn_lmin": "latch, gated, 12 b", "bmi_snn_lmem2": "latch mem. (pipel.)", "bmi_snn_lmin2": "latch, gated, 12 b (pipel.)",
             "bmi_snn_hw": "hw 20 b", "bmi_snn_min": "hw 16 b", "bmi_snn_ming": "hw 16 b gated", "bmi_snn_m12": "hw 12 b gated", "bmi_snn_sp": "hw 25 % syn.",
             "bmi_snn_sp8": "hw 12.5 % syn.", "bmi_snn_min32": "hw H=32", "bmi_snn_min16": "hw H=16"}
    fig, axs = plt.subplots(1, 2, figsize=(7.6, 3.0))
    def E(n): d = out[n]; return d.get("event_sdf", d["event"])["energy_per_bin_nJ"]
    for n in names:
        d = out[n]; fam = d["family"]
        a = d["pnr"]["instance_area_um2"] / 1e6 if "pnr" in d else np.nan
        axs[0].scatter(a, E(n), c=col[fam], marker=mk[fam], s=28, zorder=3); axs[0].annotate(short[n], (a, E(n)), fontsize=6, xytext=(3, 2), textcoords="offset points")
        if d.get("r2") is not None:
            axs[1].scatter(d["r2"], E(n), c=col[fam], marker=mk[fam], s=28, zorder=3); axs[1].annotate(short[n], (d["r2"], E(n)), fontsize=6, xytext=(3, 2), textcoords="offset points")
    axs[0].set_xscale("log"); axs[0].set_yscale("log"); axs[0].set_xlabel("instance area (mm²)"); axs[0].set_ylabel("energy per 4 ms bin (nJ), SDF where available")
    axs[1].set_yscale("log"); axs[1].set_xlabel("test R² (mean of three sessions)"); axs[1].set_ylabel("energy per 4 ms bin (nJ)")
    axs[1].axvline(0.55, color="0.6", ls=":", lw=0.8)
    for fam, lab in (("seq", "SRAM macro, sequential"), ("prog", "weights in standard cells"), ("hw", "hardwired weights")):
        axs[1].scatter([], [], c=col[fam], marker=mk[fam], s=28, label=lab)
    axs[1].legend(fontsize=6.5, frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(ROOT / "paper/figures/variants.pdf"); fig.savefig(ROOT / "paper/figures/variants.png", dpi=200)

def main():
    out = collect()
    (ROOT / "results/designs.json").write_text(json.dumps(out, indent=1, default=float))
    write_markdown(out); write_latex(out)
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "sw/make_variants_fig.py"), str(ROOT), str(ROOT / "paper/figures")], check=False)

if __name__ == "__main__":
    main()
