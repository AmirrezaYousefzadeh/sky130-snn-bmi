#!/usr/bin/env bash
# Render the final placed-and-routed DEF of bmi_snn_top to paper/figures/floorplan.png
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN_DIR="${RUN_DIR:-$ROOT/synthesis/bmi_snn_top/runs/bmi_snn_top}"
DEF="$RUN_DIR/final/def/bmi_snn_top.def"
"$ROOT/.venv/bin/python" "$ROOT/../skywater/synthesis/scripts/plot_floorplan_def.py" "$DEF" \
  --lef "$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8.lef" \
  --title "bmi_snn_top — sky130_fd_sc_hd, SRAM22 2048x32 weight macro" -o "$ROOT/paper/figures/floorplan.png"
ls -la "$ROOT/paper/figures/floorplan.png"
