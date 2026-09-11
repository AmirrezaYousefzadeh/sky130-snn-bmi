#!/usr/bin/env python3
"""Emit empty Verilog modules for cells that a routed netlist instantiates without any pin connection (tap, fill, decap,
antenna cells: physical-only, written by OpenROAD without power pins) and that the cell library's simulation models do not define.
Usage: gen_phys_stubs.py <netlist.v> <out_stubs.v> <model .v files...>"""
import re, sys
from pathlib import Path
net = Path(sys.argv[1]).read_text(errors="replace"); out = Path(sys.argv[2]); models = " ".join(Path(f).read_text(errors="replace") for f in sys.argv[3:])
defined = set(re.findall(r"^\s*module\s+([A-Za-z0-9_\\$]+)", models, re.M)) | set(re.findall(r"^\s*primitive\s+([A-Za-z0-9_\\$]+)", models, re.M))
defined |= set(re.findall(r"^\s*module\s+([A-Za-z0-9_\\$]+)", net, re.M))
inst = re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z0-9_\\\[\]$.]+)\s*\(\s*\)\s*;", net, re.M)          # empty-connection instances
used_conn = set(re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+[A-Za-z0-9_\\\[\]$.]+\s*\(\s*\.", net, re.M))          # instances with pins
stubs = sorted({c for c, _ in inst if c not in defined and c not in ("module", "wire", "input", "output", "assign")})
missing_conn = sorted({c for c in used_conn if c not in defined and c not in ("module",)})
out.write_text("// physical-only cells (no pins in the netlist): empty modules for simulation\n" + "".join(f"module {c} (); endmodule\n" for c in stubs))
print(f"{len(stubs)} physical-only cell types stubbed: {stubs[:6]}{' ...' if len(stubs) > 6 else ''}")
if missing_conn: print("WARNING: connected cells without a model:", missing_conn[:10])
