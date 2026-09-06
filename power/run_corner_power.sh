#!/usr/bin/env bash
# Voltage-scaling study: re-evaluate an existing gate-level waveform with the liberty of another corner.
# Usage: run_corner_power.sh <design> <tag> <corner>    e.g. bmi_snn_min16 bmi_snn_min16_md0_sdf ss_100C_1v40
#   VCD: sim/build_<tag>/<tag>.vcd ; netlist/SPEF: synthesis/<design>/runs/<design> (or RUN_DIR) ; out: power/out_vcd_<tag>_<corner>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$1"; TAG="$2"; CORNER="$3"
export PDK_ROOT="${PDK_ROOT:-/media/pdk}"
OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
export RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$D/runs/$D}" TOP="$D" VCD_SCOPE="tb_bmi_snn/u_dut" PERIOD_NS="${PERIOD_NS:-20}"
export LIB_SC="$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__${CORNER}.lib"
export VCD_FILE="$ROOT/sim/build_$TAG/$TAG.vcd" OUT="$ROOT/power/out_vcd_${TAG}_${CORNER}"
[[ -f "$LIB_SC" ]] || { echo "no liberty $LIB_SC"; exit 2; }
[[ -f "$VCD_FILE" ]] || { echo "no VCD $VCD_FILE"; exit 2; }
rm -rf "$OUT"; mkdir -p "$OUT"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c sta -no_splash -exit "$ROOT/power/power_corner_sta.tcl" > "$OUT/sta.log" 2>&1 || { tail -20 "$OUT/sta.log"; exit 1; }
grep -E "WORST_SETUP|^Total" "$OUT/sta.log" "$OUT/power_vcd.rpt" | head -3
