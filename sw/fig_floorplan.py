#!/usr/bin/env python3
"""Figure: placed-and-routed sequential SRAM core (bmi_snn_top) from the final DEF: standard-cell density (hex bins), the SRAM22
macro, the die outline. Fonts sized for a 0.8-linewidth figure. Writes paper/figures/floorplan.{pdf,png}."""
import re, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT = Path(__file__).resolve().parent.parent
DEF = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "synthesis/bmi_snn_top/runs/bmi_snn_top/final/def/bmi_snn_top.def"
LEF = ROOT / "synthesis/bmi_snn_top/macros/sram22_2048x32m8w8.lef"
txt = DEF.read_text(errors="ignore")
units = float(re.search(r"UNITS DISTANCE MICRONS (\d+)", txt).group(1))
die = [float(v) / units for v in re.search(r"DIEAREA \( (\d+) (\d+) \) \( (\d+) (\d+) \)", txt).groups()]
comps = re.findall(r"^\s*- (\S+) (\S+) \+ (?:PLACED|FIXED) \( (-?\d+) (-?\d+) \)", txt, flags=re.M)
phys = re.compile(r"fill|decap|tap|diode", re.I)
xs = np.array([float(x) / units for n, c, x, y in comps if not phys.search(c) and not c.startswith("sram22")])
ys = np.array([float(y) / units for n, c, x, y in comps if not phys.search(c) and not c.startswith("sram22")])
mac = [(n, c, float(x) / units, float(y) / units) for n, c, x, y in comps if c.startswith("sram22")]
size = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", LEF.read_text()).groups(); mw, mh = float(size[0]), float(size[1])
plt.rcParams.update({"font.size": 11, "axes.labelsize": 11, "xtick.labelsize": 10, "ytick.labelsize": 10})
fig, ax = plt.subplots(figsize=(7.2, 5.4))
hb = ax.hexbin(xs, ys, gridsize=(46, 30), cmap="Greens", mincnt=1, linewidths=0.2, extent=(die[0], die[2], die[1], die[3]))
cb = fig.colorbar(hb, ax=ax, pad=0.02, fraction=0.05); cb.set_label("standard cells per bin", fontsize=11); cb.ax.tick_params(labelsize=10)
for n, c, x, y in mac:
    ax.add_patch(Rectangle((x, y), mw, mh, facecolor="#6f8fbf", edgecolor="black", linewidth=1.2, alpha=0.9))
    ax.text(x + mw / 2, y + mh / 2, f"SRAM22 weight macro\n2048 x 32 b\n{mw:.0f} x {mh:.0f} um", ha="center", va="center", fontsize=11, color="white", fontweight="bold")
ax.add_patch(Rectangle((die[0], die[1]), die[2] - die[0], die[3] - die[1], fill=False, edgecolor="black", linewidth=1.8))
ax.text(0.5 * (mac[0][2] + mw + die[2]) if mac else 0.8 * die[2], die[3] - 130, f"standard-cell logic\n{len(xs):,} logic cells: controller,\n64 membranes, 4 adders, read-out\n(taps, diodes, fillers not shown)", ha="center", va="top", fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#777777", linewidth=0.6))
ax.set_xlim(die[0] - 20, die[2] + 20); ax.set_ylim(die[1] - 20, die[3] + 20); ax.set_aspect("equal")
ax.set_xlabel("x (um)"); ax.set_ylabel("y (um)")
ax.set_title(f"die {die[2]-die[0]:.0f} x {die[3]-die[1]:.0f} um", fontsize=11)
fig.tight_layout()
FIG = ROOT / "paper/figures"; fig.savefig(FIG / "floorplan.pdf"); fig.savefig(FIG / "floorplan.png", dpi=200)
print(f"floorplan figure: {len(xs)} standard cells, macro {mw} x {mh} um, die {die}")
