#!/usr/bin/env python3
"""Voltage-scaling study: collect power/run_corner_set.sh results (existing SDF waveforms re-evaluated with the liberty
of other PVT corners) into results/corners.json and paper/corners_table.tex."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from collect_results import parse_group_table, parse_tb_summary, RATE
ROOT = Path(__file__).resolve().parent.parent
TCLK = 20.0
CORNERS = [("tt_025C_1v80", "TT 1.80 V 25 °C", "1.80", "25"), ("tt_100C_1v80", "TT 1.80 V 100 °C", "1.80", "100"),
           ("ss_100C_1v40", "SS 1.40 V 100 °C", "1.40", "100"), ("ss_n40C_1v40", "SS 1.40 V -40 °C", "1.40", "-40"),
           ("ss_n40C_1v28", "SS 1.28 V -40 °C", "1.28", "-40")]
TLABEL = {"bmi_snn_min": "hardwired 16-bit", "bmi_snn_ming": "hardwired 16-bit, gated", "bmi_snn_sp": "hardwired 12-bit, gated, 25\\,\\% synapses", "bmi_snn_min32": "hardwired 16-bit, $H{=}32$", "bmi_snn_min16": "hardwired 16-bit, $H{=}16$"}
LABEL = {"bmi_snn_hw": "hardwired 64x20 b", "bmi_snn_min": "hardwired 64x16 b", "bmi_snn_min32": "hardwired H=32", "bmi_snn_min16": "hardwired H=16",
         "bmi_snn_ming": "hw 16 b, gated", "bmi_snn_m12": "hw 12 b, gated", "bmi_snn_sp": "hw pruned 25 %", "bmi_snn_sp8": "hw pruned 12.5 %", "bmi_snn_lmin": "latch mem., gated, 12 b", "bmi_snn_lmin2": "latch mem., gated, 12 b, pipelined W2"}

def cycles(log: Path):
    t = log.read_text(errors="replace"); m = re.search(r"MEASURED: cycles_from_dump_start=(\d+)", t)
    tb = parse_tb_summary(log); return (int(m.group(1)) if m else tb.get("cycles")), tb.get("bins")

def one(design, corner):
    tag = f"{design}_md0_sdf"; d = ROOT / "power" / (f"out_vcd_{tag}" if corner == "tt_025C_1v80" else f"out_vcd_{tag}_{corner}")
    rpt = d / "power_vcd.rpt"; log = ROOT / f"sim/build_{tag}/vvp.log"
    if not (rpt.exists() and log.exists()): return None
    g = parse_group_table(rpt); cyc, bins = cycles(log)
    P = g["Total"]["total"]; E = P * cyc * TCLK * 1e-9 / bins * 1e9
    r = {"energy_per_bin_nJ": E, "power_uW": P * 1e6, "leakage_active_uW": g["Total"]["leakage"] * 1e6}
    s = d / "slack.txt"
    if s.exists():
        ws = float(re.search(r"setup_ws_ns (\S+)", s.read_text()).group(1)) * 1e9   # OpenSTA reports seconds
        r["setup_ws_ns"] = ws; r["fmax_MHz"] = 1e3 / (TCLK - ws) if TCLK - ws > 0 else None
    idle = ROOT / "power" / (f"out_vcd_{design}_idle_sdf" if corner == "tt_025C_1v80" else f"out_vcd_{design}_idle_sdf_{corner}") / "power_vcd.rpt"
    if idle.exists():
        gi = parse_group_table(idle); r["leakage_uW"] = gi["Total"]["leakage"] * 1e6
        r["avg_power_uW_250Hz_clkstopped"] = E * RATE * 1e-3 + r["leakage_uW"]
    return r

def main():
    out = {}
    for design in LABEL:
        row = {c: one(design, c) for c, *_ in CORNERS}
        if any(row.values()): out[design] = row
    (ROOT / "results/corners.json").write_text(json.dumps(out, indent=1))
    # LaTeX: one block per design, rows = corners
    L = ["\\begin{tabular}{llrrrrr}", "\\toprule",
         "Core & Corner & $f_{\\max}$ (MHz) & $E_{\\mathrm{bin}}$ (nJ) & rel. & Leakage (\\si{\\micro\\watt}) & $P_{\\mathrm{avg}}$ (\\si{\\micro\\watt}) \\\\", "\\midrule"]
    def f(x, nd=3): return "--" if x is None else (f"{x:,.0f}" if abs(x) >= 1000 else f"{x:.{nd}g}")
    TABLE_DESIGNS = ["bmi_snn_min", "bmi_snn_ming", "bmi_snn_sp", "bmi_snn_min32", "bmi_snn_min16"]   # (no SDF waveform for the latch cores)   # keep the table short
    TABLE_CORNERS = ["tt_025C_1v80", "tt_100C_1v80", "ss_100C_1v40", "ss_n40C_1v40", "ss_n40C_1v28"]
    for design, row in out.items():
        if design not in TABLE_DESIGNS: continue
        base = row.get("tt_025C_1v80", {}) or {}
        first = True
        for c, lab, *_ in CORNERS:
            if c not in TABLE_CORNERS: continue
            r = row.get(c)
            if not r: continue
            rel = r["energy_per_bin_nJ"] / base["energy_per_bin_nJ"] if base.get("energy_per_bin_nJ") else None
            L.append(f"{TLABEL.get(design, LABEL[design]) if first else ''} & {lab} & {f(r.get('fmax_MHz'), 3)} & {f(r['energy_per_bin_nJ'])} & {f(rel, 2)} & {f(r.get('leakage_uW'))} & {f(r.get('avg_power_uW_250Hz_clkstopped'))} \\\\")
            first = False
        L.append("\\midrule")
    L[-1] = "\\bottomrule"; L.append("\\end{tabular}%")
    (ROOT / "paper/corners_table.tex").write_text("\n".join(L) + "\n")
    # macros: \eC<Design><Corner>, \fC.., \leakC.., \relC..  (design short names as in collect_designs, corners tt, ttHot, ssHot14, ssCold14, ssCold12)
    SH = {"bmi_snn_hw": "Hw", "bmi_snn_min": "Min", "bmi_snn_min32": "MinH", "bmi_snn_min16": "MinS", "bmi_snn_ming": "MinG", "bmi_snn_m12": "MinT",
          "bmi_snn_sp": "Sp", "bmi_snn_sp8": "SpE", "bmi_snn_lmin": "LmMin", "bmi_snn_lmin2": "LmMinP"}
    CS = {"tt_025C_1v80": "Tt", "tt_100C_1v80": "TtHot", "ss_100C_1v40": "SsHotA", "ss_n40C_1v40": "SsColdA", "ss_n40C_1v28": "SsColdB"}
    M = []
    for design in LABEL:
        row = out.get(design, {}); base = (row.get("tt_025C_1v80") or {}).get("energy_per_bin_nJ")
        for c, cs in CS.items():
            r = row.get(c) or {}
            for k, v, nd in (("eC", r.get("energy_per_bin_nJ"), 3), ("fC", r.get("fmax_MHz"), 3), ("leakC", r.get("leakage_uW"), 3),
                             ("pavgC", r.get("avg_power_uW_250Hz_clkstopped"), 3), ("relC", (r.get("energy_per_bin_nJ") / base) if (base and r.get("energy_per_bin_nJ")) else None, 2)):
                M.append(f"\\newcommand{{\\{k}{SH[design]}{cs}}}{{{f(v, nd) if v is not None else '\\textcolor{red}{?}'}}}")
    (ROOT / "paper/numbers_corners.tex").write_text("% auto-generated by sw/collect_corners.py\n" + "\n".join(M) + "\n")
    for design, row in out.items():
        print(design, {c: (f(r['energy_per_bin_nJ']), f(r.get('fmax_MHz'))) for c, r in row.items() if r})

if __name__ == "__main__":
    main()
