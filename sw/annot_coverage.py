#!/usr/bin/env python3
"""Round 10: fraction of the design's cell pins that received their activity from the simulation. A pin is covered when it was
annotated directly (set_power_activity -pins on the dumped cell pin) or when the net it connects to was annotated through its driver
(the nets of the dumped scope). Reads the netlist and the coverage lists written by the generated activity script
(power/toggles_to_activity.py: annot_found_pins.txt, annot_found_nets.txt). Usage: annot_coverage.py <netlist.v> <out_dir> [--json]"""
import re, sys, json
from pathlib import Path
nl, out = Path(sys.argv[1]), Path(sys.argv[2])
txt = nl.read_text(errors="ignore")
SKIP = ("module", "wire", "input", "output", "assign", "reg", "endmodule", "supply0", "supply1", "inout")
pins = []; cells = 0
for m in re.finditer(r"^\s*([A-Za-z_][\w$]*)\s+(\\?\S+)\s*\((.*?)\);", txt, flags=re.S | re.M):
    if m.group(1) in SKIP: continue
    cells += 1; inst = m.group(2).lstrip("\\")
    for pin, net in re.findall(r"\.(\w+)\(\s*([^()]*?)\s*\)", m.group(3)):
        if pin in ("VPWR", "VGND", "VPB", "VNB", "VDD", "VSS", "VNW", "VPW", "vdd", "gnd", "VDDPE", "VDDCE", "VSSE"): continue
        pins.append((inst + "/" + pin, net.strip()))
def rd(f):
    p = out / f; return set(l.strip().replace("\\", "") for l in p.read_text().splitlines() if l.strip()) if p.exists() else set()
fp = rd("annot_found_pins.txt"); fn = rd("annot_found_nets.txt")
def norm(n): return n.replace("\\", "").strip()
cov = sum(1 for p, n in pins if norm(p) in fp or norm(n) in fn)
# constant nets (1'b0/1'b1) are not activity carriers; count them separately
const = sum(1 for p, n in pins if re.match(r"^\d+'[bhd]", n))
res = {"cells": cells, "pins": len(pins), "pins_covered": cov, "pins_constant": const, "coverage": cov / len(pins) if pins else None,
       "coverage_excl_constant": (cov / (len(pins) - const)) if pins and len(pins) > const else None, "found_pins": len(fp), "found_nets": len(fn)}
if "--json" in sys.argv: print(json.dumps(res))
else: print(f"{nl.name}: {cells} cells, {len(pins)} pins, {cov} covered ({100*res['coverage']:.2f} %), {const} on constant nets ({100*(res['coverage_excl_constant'] or 0):.2f} % of the rest)")
json.dump(res, open(out / "annot_coverage.json", "w"), indent=1)
