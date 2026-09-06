#!/usr/bin/env bash
# Time-windowed power of bmi_snn_top: ./power/run_time_power.sh <vcd> [windows] [out_dir]
# (u_imem columns in the CSV = the weight SRAM u_wmem; u_dmem columns are absent/zero.)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; POWER="$ROOT/power"
export ROOT PDK_ROOT="${PDK_ROOT:-/media/pdk}"
OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
VCD="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"; WINDOWS="${2:-500}"
RUN_DIR="${RUN_DIR:-$ROOT/synthesis/bmi_snn_top/runs/bmi_snn_top}"
OUT="${3:-$POWER/out_$(basename "$VCD" .vcd)_time}"
DESIGN_PERIOD_NS="${DESIGN_PERIOD_NS:-25}"
export LIB_SC="${LIB_SC:-$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib}"
export LIB_SRAM="${LIB_SRAM:-$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80.lib}"
rm -rf "$OUT"; mkdir -p "$OUT"
python3 "$POWER/vcd_to_windows.py" "$VCD" --scope tb_bmi_snn.u_dut --windows "$WINDOWS" --design-period-ns "$DESIGN_PERIOD_NS" -o "$OUT/windows.json" --sta-tcl "$OUT/windows.tcl"
export RUN_DIR POWER_OUT="$OUT" ACTIVITY_TCL="$OUT/windows.tcl"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c sta -no_splash -exit "$POWER/power_time_sta.tcl" > "$OUT/sta_time.log" 2>&1 || { tail -20 "$OUT/sta_time.log"; exit 1; }
python3 "$POWER/emit_time_power.py" --windows-json "$OUT/windows.json" --sta-log "$OUT/sta_time.log" --vcd-out "$OUT/power_vs_time.vcd" --csv-out "$OUT/power_vs_time.csv" --summary-out "$OUT/power_time_summary.txt"
cat "$OUT/power_time_summary.txt" 2>/dev/null | head -20
