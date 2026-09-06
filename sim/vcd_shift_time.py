#!/usr/bin/env python3
"""Shift VCD timestamps so that the first timestamp becomes 0 (for dumps started after a load phase)."""
import sys
from pathlib import Path
p = Path(sys.argv[1]); tmp = p.with_suffix(p.suffix + ".tmp"); off = None
with p.open("r", errors="replace") as fin, tmp.open("w") as fout:
    for line in fin:
        if line.startswith("#"):
            t = int(line[1:].strip() or 0)
            if off is None: off = t
            fout.write(f"#{t - off}\n")
        else:
            fout.write(line)
tmp.replace(p); print(f"shifted {p} by {off}")
