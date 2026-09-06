#!/usr/bin/env python3
"""Cycle accounting for the RISC-V baseline from a tb_fw_mnist VCD (level-1 dump of u_soc).
Reports awake cycles (sram_clk_en high) during the decode phase = between the 2nd and 3rd wake events."""
import sys, re
from pathlib import Path
vcd = Path(sys.argv[1]); n_bins = int(sys.argv[2]) if len(sys.argv) > 2 else 16
ids = {}; scopes = []
want = {"clk", "sram_clk_en", "gpio_done", "wake", "halted"}
vals = {}; t = 0; last_t = 0
clk_rises = 0; en_cycles = 0
events = []  # (time, name, value)
with vcd.open(errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        if line.startswith("$scope"): scopes.append(line.split()[2]); continue
        if line.startswith("$upscope"): scopes.pop(); continue
        if line.startswith("$var"):
            m = re.match(r"\$var\s+\S+\s+(\d+)\s+(\S+)\s+(\S+)", line)
            if m and int(m.group(1)) == 1 and m.group(3) in want and ".".join(scopes).endswith("u_soc"):
                ids.setdefault(m.group(2), m.group(3))
            continue
        if line[0] == "#": t = int(line[1:]); continue
        if line[0] in "01" and line[1:] in ids:
            name = ids[line[1:]]; v = int(line[0]); old = vals.get(name)
            vals[name] = v
            if name == "clk" and old == 0 and v == 1:
                clk_rises += 1
                if vals.get("sram_clk_en") == 1: en_cycles += 1
            elif name != "clk" and old != v:
                events.append((t, clk_rises, name, v))
wakes = [e for e in events if e[2] == "wake" and e[3] == 1]
done = [e for e in events if e[2] == "gpio_done" and e[3] == 1]
en_edges = [e for e in events if e[2] == "sram_clk_en"]
print(f"total clk cycles {clk_rises}, awake cycles {en_cycles}, wakes at cycles {[w[1] for w in wakes]}, gpio_done at {[d[1] for d in done]}")
# decode phase: from the wake preceding gpio_done to gpio_done
w2 = max(w[1] for w in wakes if w[1] < done[0][1])
dec = done[0][1] - w2
print(f"decode phase: {dec} cycles for {n_bins} bins -> {dec / n_bins:.0f} cycles/bin (incl. wake latency)")
# awake segments
segs = []; start = None
for e in en_edges:
    if e[3] == 1: start = e[1]
    elif start is not None: segs.append((start, e[1])); start = None
print("awake segments (cycles):", [(a, b, b - a) for a, b in segs])
import json
out = Path(__file__).resolve().parent.parent / "results" / "riscv_cycles.json"
json.dump({"vcd": str(vcd), "n_bins": n_bins, "total_cycles": clk_rises, "awake_cycles": en_cycles,
           "decode_cycles": dec, "cycles_per_bin": dec / n_bins, "awake_segments": [(a, b, b - a) for a, b in segs]},
          open(out, "w"), indent=1)
print("wrote", out)
