#!/usr/bin/env bash
# Average power / energy of bmi_snn_top from a (gate-level) VCD + OpenLane netlist/SPEF.
# Usage: ./power/run_avg_power.sh <vcd> [out_dir]     env: RUN_DIR, DESIGN_PERIOD_NS (default 20), LIB corner
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; POWER="$ROOT/power"
export ROOT PDK_ROOT="${PDK_ROOT:-/media/pdk}"
OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
VCD="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
RUN_DIR="${RUN_DIR:-$ROOT/synthesis/bmi_snn_top/runs/bmi_snn_top}"
OUT="${2:-$POWER/out_$(basename "$VCD" .vcd)}"
DESIGN_PERIOD_NS="${DESIGN_PERIOD_NS:-25}"
SCOPE="${SCOPE:-tb_bmi_snn.u_dut}"
export LIB_SC="${LIB_SC:-$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib}"
export LIB_SRAM="${LIB_SRAM:-$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80.lib}"
rm -rf "$OUT"; mkdir -p "$OUT"
echo "==> [1/3] activity from $VCD"
python3 "$POWER/vcd_to_activity.py" "$VCD" --scope "$SCOPE" --design-period-ns "$DESIGN_PERIOD_NS" -o "$OUT/activity.json" --sta-tcl "$OUT/activity.tcl"
export RUN_DIR POWER_OUT="$OUT" ACTIVITY_TCL="$OUT/activity.tcl"
echo "==> [2/3] OpenSTA power (period ${DESIGN_PERIOD_NS} ns)"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c sta -no_splash -exit "$POWER/power_activity_sta.tcl" > "$OUT/sta.log" 2>&1 || { tail -30 "$OUT/sta.log"; exit 1; }
echo "==> [3/3] summary"
python3 "$POWER/summarize_energy.py" --activity-json "$OUT/activity.json" --power-rpt "$OUT/power_activity.rpt" --clock-rpt "$OUT/power_clock_tree.rpt" --design-period-ns "$DESIGN_PERIOD_NS" -o "$OUT/power_energy.txt"
cat "$OUT/power_energy.txt"
