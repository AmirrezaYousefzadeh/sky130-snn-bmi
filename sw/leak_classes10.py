#!/usr/bin/env python3
"""Round 10 (E10): leakage by cell class (logic, fill, decap, tap, diode, endcap) of one per-instance OpenSTA report, with the cell
masters of the netlist (classification of sw/leak_split6.py). Usage: leak_classes10.py <power_vcd_by_instance.rpt> <netlist.v> [-o out.json]"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from leak_split6 import split
rpt, nl = sys.argv[1], sys.argv[2]
out, unm = split(rpt, nl); tot = sum(v[1] for v in out.values())
res = {k: dict(n=v[0], leak_uW=v[1]) for k, v in out.items()} | dict(total_uW=tot, phys_uW=tot - out["logic"][1], unmatched=unm)
if "-o" in sys.argv: json.dump(res, open(sys.argv[sys.argv.index("-o") + 1], "w"), indent=1)
print(f"total {tot:.4f} uW: logic {out['logic'][1]:.4f} ({out['logic'][0]:,}) fill {out['fill'][1]:.4f} ({out['fill'][0]:,}) decap {out['decap'][1]:.4f} ({out['decap'][0]:,}) tap {out['tap'][1]:.4f} ({out['tap'][0]:,}) diode {out['diode'][1]:.4f} unmatched {unm}")
