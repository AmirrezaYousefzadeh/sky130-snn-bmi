#!/usr/bin/env python3
"""Round 6 (E3a): leakage of the physical-only cells split by class (fill, decap, tap, diode/antenna, endcap) for every kit and core,
from the per-instance OpenSTA report of the idle run and the cell masters of the routed netlist. Writes results/leak_split6.csv and
results/leak_split6.json (read by sw/collect_pdks5.py for the \\leakFill<Kit><Core> / \\leakDecap / \\leakTap macros)."""
import re, json, csv
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; ORFS = Path("/media/pdk/OpenROAD-flow-scripts/flow")
CLASSES = [("decap", re.compile(r"decap|fillcap", re.I)), ("fill", re.compile(r"fill", re.I)), ("tap", re.compile(r"tap|filltie|welltap", re.I)),
           ("diode", re.compile(r"diode|antenna", re.I)), ("endcap", re.compile(r"endcap", re.I))]
def classify(master):
    for name, rx in CLASSES:
        if rx.search(master): return name
    return None
def cell_map(netlist):
    m = {}
    for mm in re.finditer(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(\\?\S+)\s*\(', open(netlist, errors="ignore").read(), flags=re.M):
        if mm.group(1) in ("module", "wire", "input", "output", "assign", "reg", "endmodule"): continue
        m[mm.group(2).lstrip("\\")] = mm.group(1)
    return m
def split(rpt, netlist):
    cm = cell_map(netlist); out = {c: [0, 0.0] for c, _ in CLASSES}; out["logic"] = [0, 0.0]; unmatched = 0
    for line in open(rpt, errors="ignore"):
        f = line.split()
        if len(f) < 5: continue
        try: leak = float(f[2])
        except ValueError: continue
        c = cm.get(f[4].lstrip("\\"))
        if c is None: unmatched += 1; continue
        k = classify(c) or "logic"; out[k][0] += 1; out[k][1] += leak * 1e6
    return out, unmatched
jobs = []   # (kit, core, rpt, netlist)
D = json.load(open(ROOT / "results/designs.json"))
for d in D:
    rpt = ROOT / f"power/out_vcd_{d}_5m_idle_full/power_vcd_by_instance.rpt"; nl = ROOT / f"synthesis/{d}/runs/{d}_5m/final/nl/{d}.nl.v"
    if rpt.exists() and nl.exists(): jobs.append(("sky130", d.replace("bmi_snn_", ""), rpt, nl))
P = json.load(open(ROOT / "results/pdks5.json"))
PLAT = {"nangate45": "nangate45", "ihp": "ihp-sg13g2", "asap7": "asap7", "asap7sram": "asap7"}
for key in P:
    kit, core = key.split("/"); d = f"bmi_snn_{core}"; rpt = ROOT / f"power/out_vcd_pdk5_{kit}_{core}_idle_full/power_vcd_by_instance.rpt"
    if kit == "sky130": continue   # covered by the designs.json loop above
    if kit == "gf180": nl = ROOT / f"synthesis/pdk_gf180/{d}/runs/{d}_5m/final/nl/{d}.nl.v"
    else: nl = ORFS / f"results/{PLAT[kit]}/{d}_5m{'_sram' if kit == 'asap7sram' else ''}/base/6_final.v"
    if rpt.exists() and nl.exists(): jobs.append((kit, core, rpt, nl))
rows = []; J = {}
for kit, core, rpt, nl in jobs:
    out, unm = split(rpt, nl); tot = sum(v[1] for v in out.values()); phys = tot - out["logic"][1]
    J[f"{kit}/{core}"] = {k: dict(n=v[0], leak_uW=v[1]) for k, v in out.items()} | dict(total_uW=tot, phys_uW=phys, unmatched=unm)
    for k, v in out.items(): rows.append(dict(kit=kit, core=core, cls=k, n_cells=v[0], leak_uW=round(v[1], 6)))
    print(f"{kit:10s} {core:8s} total {tot:9.3f} uW  logic {out['logic'][1]:8.3f}  fill {out['fill'][1]:8.3f} ({out['fill'][0]:,})  decap {out['decap'][1]:8.3f} ({out['decap'][0]:,})  tap {out['tap'][1]:7.3f} ({out['tap'][0]:,})  diode {out['diode'][1]:7.3f} ({out['diode'][0]:,})  endcap {out['endcap'][1]:6.3f} ({out['endcap'][0]:,})  unmatched {unm}")
with open(ROOT / "results/leak_split6.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["kit", "core", "cls", "n_cells", "leak_uW"]); w.writeheader(); w.writerows(rows)
json.dump(J, open(ROOT / "results/leak_split6.json", "w"), indent=1); print("wrote results/leak_split6.csv /.json", len(J), "kit/core pairs")
