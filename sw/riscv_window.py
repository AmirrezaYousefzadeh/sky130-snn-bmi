#!/usr/bin/env python3
"""E7 (round 5): decoding window of the RISC-V SoC waveform in VCD time units: from the last `wake` before `gpio_done` (the
firmware wakes the core once for the whole decode of N bins) to the rising edge of `gpio_done`. Also counts clock cycles and
awake cycles inside the window. Usage: riscv_window.py <vcd> [n_bins] -> JSON on stdout (begin, end, timescale, cycles...)."""
import sys, re, json, subprocess
from pathlib import Path
vcd = Path(sys.argv[1]); n_bins = int(sys.argv[2]) if len(sys.argv) > 2 else 16
want = {"clk", "sram_clk_en", "gpio_done", "wake"}; ids = {}; scopes = []; tscale = "1ns"
with vcd.open(errors="replace") as f:
    for line in f:
        if line.startswith("$timescale"):
            body = line.replace("$timescale", "").replace("$end", "").strip()
            if not body: body = next(f).replace("$end", "").strip()
            tscale = body
        elif line.startswith("$scope"): scopes.append(line.split()[2])
        elif line.startswith("$upscope"): scopes.pop()
        elif line.startswith("$var"):
            m = re.match(r"\$var\s+\S+\s+(\d+)\s+(\S+)\s+(\S+)", line)
            if m and int(m.group(1)) == 1 and m.group(3) in want and ".".join(scopes).endswith("u_soc"): ids.setdefault(m.group(2), m.group(3))
        elif line.startswith("$enddefinitions"): break
pat = "^(#[0-9]+|(" + "|".join("[01]" + re.escape(v) for v in ids) + "))$"
proc = subprocess.Popen(["grep", "-a", "-E", pat, str(vcd)], stdout=subprocess.PIPE, text=True, errors="replace")   # streamed: a 5 GB waveform must not be held in memory
t = 0; vals = {}; wakes = []; done = None; rises = []
for line in proc.stdout:
    line = line.rstrip("\n")
    if not line: continue
    if line[0] == "#": t = int(line[1:]); continue
    name = ids[line[1:]]; v = int(line[0]); old = vals.get(name); vals[name] = v
    if name == "clk" and old == 0 and v == 1: rises.append((t, vals.get("sram_clk_en", 0)))
    elif name == "wake" and old != v and v == 1: wakes.append(t)
    elif name == "gpio_done" and old != v and v == 1 and done is None: done = t
begin = max(w for w in wakes if w < done); end = done
cyc = [r for r in rises if begin <= r[0] <= end]; awake = sum(1 for r in cyc if r[1] == 1)
res = {"vcd": str(vcd), "timescale": tscale, "begin": begin, "end": end, "n_bins": n_bins, "cycles_in_window": len(cyc), "awake_cycles_in_window": awake,
       "cycles_per_bin": len(cyc) / n_bins, "wakes": wakes, "gpio_done": done}
print(json.dumps(res, indent=1))
