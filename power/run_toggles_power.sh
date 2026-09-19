#!/usr/bin/env bash
# Per-pin OpenSTA power from accumulated toggle counts (tools/vcd_toggles output) instead of a stored VCD.
# Usage: run_toggles_power.sh core|riscv <toggles.tsv> <out_dir>      Env as run_vcd_power.sh (DESIGN, RUN_DIR, PERIOD_NS, MACRO_INST,
#   LIB_SC, LIB_SRAM, NETLIST, SPEF) plus LIB_TIME_UNIT_S (1e-9 default; 1e-12 for ASAP7) and VCD_SCOPE override.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"
KIND="$1"; TSV="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"; OUT="$3"
export PDK_ROOT="${PDK_ROOT:-/media/pdk}"; OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
if [[ "$KIND" == "core" ]]; then
  DESIGN="${DESIGN:-bmi_snn_top}"
  export RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$DESIGN/runs/$DESIGN}" TOP="$DESIGN" VCD_SCOPE="${VCD_SCOPE:-tb_bmi_snn/u_dut}" PERIOD_NS="${PERIOD_NS:-20}" MACRO_INST="${MACRO_INST:-u_wmem}"
  export LIB_SC="${LIB_SC:-$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib}"
  export LIB_SRAM="${LIB_SRAM:-$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80.lib}"
else
  export RUN_DIR="${RUN_DIR:-$SKY/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc}" TOP=sky130_vex2_soc VCD_SCOPE="${VCD_SCOPE:-tb_fw_mnist/u_soc}" PERIOD_NS="${PERIOD_NS:-20}" MACRO_INST="u_imem u_dmem"
  export LIB_SC="${LIB_SC:-$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_ms/lib/sky130_fd_sc_ms__tt_025C_1v80.lib}"
  export LIB_SRAM="${LIB_SRAM:-$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80.lib}"
fi
export OUT; rm -rf "$OUT"; mkdir -p "$OUT"
PERIOD_S=$(python3 -c "print($PERIOD_NS * ${LIB_TIME_UNIT_S:-1e-9})")
python3 "$ROOT/power/toggles_to_activity.py" "$TSV" --scope "$VCD_SCOPE" --period-s "$PERIOD_S" -o "$OUT/activity.tcl" --summary "$OUT/activity_summary.json" | tee "$OUT/toggles.log"
export ACT_TCL="$OUT/activity.tcl"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c sta -no_splash -exit "$ROOT/power/power_toggles_sta.tcl" > "$OUT/sta.log" 2>&1 || { tail -20 "$OUT/sta.log"; exit 1; }
grep -E "toggles_to_activity|WROTE" "$OUT/sta.log"; grep -A12 "Group" "$OUT/power_vcd.rpt" | head -14
