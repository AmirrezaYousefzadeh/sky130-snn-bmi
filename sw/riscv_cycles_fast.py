#!/usr/bin/env python3
"""Fast cycle accounting for the RISC-V baseline: grep-prefilter the huge VCD to the 5 signals of interest."""
import sys, re, json, subprocess
from pathlib import Path
vcd = Path(sys.argv[1]); n_bins = int(sys.argv[2]) if len(sys.argv) > 2 else 16
want = {"clk", "sram_clk_en", "gpio_done", "wake", "halted"}
ids = {}; scopes = []
with vcd.open(errors="replace") as f:
    for line in f:
        if line.startswith("$scope"): scopes.append(line.split()[2])
        elif line.startswith("$upscope"): scopes.pop()
        elif line.startswith("$var"):
            m = re.match(r"\$var\s+\S+\s+(\d+)\s+(\S+)\s+(\S+)", line)
            if m and int(m.group(1)) == 1 and m.group(3) in want and ".".join(scopes).endswith("u_soc"):
                ids.setdefault(m.group(2), m.group(3))
        elif line.startswith("$enddefinitions"): break
pat = "^(" + "|".join("[01]" + re.escape(v) for v in ids) + ")$"
out = subprocess.run(["grep", "-a", "-E", pat, str(vcd)], capture_output=True, text=True, errors="replace").stdout.splitlines()
vals = {}; clk_rises = 0; en_cycles = 0; events = []
for line in out:
    name = ids[line[1:]]; v = int(line[0]); old = vals.get(name); vals[name] = v
    if name == "clk" and old == 0 and v == 1:
        clk_rises += 1
        if vals.get("sram_clk_en") == 1: en_cycles += 1
    elif name != "clk" and old != v: events.append((clk_rises, name, v))
wakes = [e[0] for e in events if e[1] == "wake" and e[2] == 1]
done = [e[0] for e in events if e[1] == "gpio_done" and e[2] == 1]
w2 = max(w for w in wakes if w < done[0]); dec = done[0] - w2
segs = []; start = None
for c, name, v in events:
    if name != "sram_clk_en": continue
    if v == 1: start = c
    elif start is not None: segs.append((start, c, c - start)); start = None
res = {"vcd": str(vcd), "n_bins": n_bins, "total_cycles": clk_rises, "awake_cycles": en_cycles, "decode_cycles": dec,
       "cycles_per_bin": dec / n_bins, "wakes_at_cycles": wakes, "gpio_done_at": done, "awake_segments": segs}
print(json.dumps(res, indent=1))
import os
outp = Path(os.environ.get("CYCLES_OUT", Path(__file__).resolve().parent.parent / "results" / "riscv_cycles.json")); json.dump(res, open(outp, "w"), indent=1); print("wrote", outp, file=sys.stderr)
