#!/usr/bin/env python3
"""Generate functional (zero-delay) Verilog models of standard cells from a liberty file, for gate-level simulation when a
library ships no Verilog (NanGate45 in OpenROAD-flow-scripts). Handles combinational functions, flip-flops (ff groups with
clear/preset), latches, integrated clock gates and three-state buffers. Usage: liberty2verilog.py <lib> <out.v> [cell ...]"""
import re, sys
from pathlib import Path
lib = Path(sys.argv[1]).read_text(errors="replace"); out = Path(sys.argv[2]); only = set(sys.argv[3:])
def lib2v(expr):
    e = expr.strip().strip('"')
    e = re.sub(r"([A-Za-z0-9_\)])\s*'", r"~\1", e)              # postfix ' negation
    e = e.replace("!", "~").replace("*", "&").replace("+", "|")
    e = re.sub(r"([A-Za-z0-9_\)])\s+([A-Za-z0-9_~\(])", r"\1 & \2", e)  # implicit AND by juxtaposition
    return e
cells = list(re.finditer(r"\n\s*cell\s*\(\s*\"?([A-Za-z0-9_]+)\"?\s*\)\s*\{", lib)); mods = []
for i, m in enumerate(cells):
    name = m.group(1)
    if only and name not in only: continue
    body = lib[m.end(): cells[i + 1].start() if i + 1 < len(cells) else len(lib)]
    pins = [(p.group(1), p.group(2)) for p in re.finditer(r"pin\s*\(\s*\"?([A-Za-z0-9_]+)\"?\s*\)\s*\{(.*?)\n\s*\}\n", body, re.S)]
    ins = [n for n, b in pins if re.search(r"direction\s*:\s*input", b)]; outs = [(n, b) for n, b in pins if re.search(r"direction\s*:\s*output", b)]
    ff = re.search(r"ff\s*\(\s*\"?(\w+)\"?\s*,\s*\"?(\w+)\"?\s*\)\s*\{(.*?)\}", body, re.S); la = re.search(r"latch\s*\(\s*\"?(\w+)\"?\s*,\s*\"?(\w+)\"?\s*\)\s*\{(.*?)\}", body, re.S)
    icg = "clock_gating_integrated_cell" in body
    ports = ins + [n for n, _ in outs]
    ports = [n for n in ports if n not in ("VDD", "VSS", "VPWR", "VGND", "VNW", "VPW", "VPB", "VNB")]
    ins = [n for n in ins if n in ports]; outs = [(n, b) for n, b in outs if n in ports]
    L = [f"module {name} ({', '.join(ports)});"] + [f"  input {n};" for n in ins] + [f"  output {n};" for n, _ in outs]
    L.append("  supply1 VDD; supply0 VSS; supply1 VPWR; supply0 VGND;   // power pins referenced by some liberty functions")
    if ff or la:
        g = ff or la; iq, iqn, gb = g.group(1), g.group(2), g.group(3)
        L.append(f"  reg {iq}; wire {iqn} = ~{iq};")
        if ff:
            clk = lib2v(re.search(r"clocked_on\s*:\s*\"([^\"]+)\"", gb).group(1)); nxt = lib2v(re.search(r"next_state\s*:\s*\"([^\"]+)\"", gb).group(1))
            clr = re.search(r"clear\s*:\s*\"([^\"]+)\"", gb); pre = re.search(r"preset\s*:\s*\"([^\"]+)\"", gb)
            edge = "negedge" if clk.startswith("~") else "posedge"; clks = clk.lstrip("~")
            sens = [f"{edge} {clks}"] + ([f"posedge {lib2v(clr.group(1)).lstrip('~')}"] if clr else []) + ([f"posedge {lib2v(pre.group(1)).lstrip('~')}"] if pre else [])
            L.append(f"  always @({' or '.join(sens)})")
            conds = []
            if clr: conds.append(f"if ({lib2v(clr.group(1))}) {iq} <= 1'b0;")
            if pre: conds.append(f"{'else ' if conds else ''}if ({lib2v(pre.group(1))}) {iq} <= 1'b1;")
            conds.append(f"{'else ' if conds else ''}{iq} <= {nxt};")
            L.append("    " + " ".join(conds))
        else:
            en = lib2v(re.search(r"enable\s*:\s*\"([^\"]+)\"", gb).group(1)); din = lib2v(re.search(r"data_in\s*:\s*\"([^\"]+)\"", gb).group(1))
            L.append(f"  always @(*) if ({en}) {iq} = {din};")
    elif icg:   # integrated clock gate: latch the enable while the clock is low
        clk = [n for n in ins if n in ("CK", "CLK")][0]; en = [n for n in ins if n in ("E", "EN", "ENA", "GATE")][0]; te = [n for n in ins if n in ("SE", "TE", "SCE")]
        L.append(f"  reg IQ; always @(*) if (!{clk}) IQ = {en}{' | ' + te[0] if te else ''};")
    for n, b in outs:
        fn = re.search(r"function\s*:\s*\"([^\"]+)\"", b); ts = re.search(r"three_state\s*:\s*\"([^\"]+)\"", b)
        if fn:
            e = lib2v(fn.group(1))
            L.append(f"  assign {n} = {lib2v(ts.group(1))} ? 1'bz : ({e});" if ts else f"  assign {n} = {e};")
    L.append("endmodule\n"); mods.append("\n".join(L))
out.write_text("// functional models generated from the liberty file by sim/liberty2verilog.py\n`timescale 1ns/1ps\n" + "\n".join(mods))
print(f"{len(mods)} cell models written to {out}")
