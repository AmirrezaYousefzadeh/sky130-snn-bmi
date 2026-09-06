#!/usr/bin/env bash
# Per-net VCD-annotated OpenSTA power.  Usage: run_vcd_power.sh core|riscv <vcd> [out_dir]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"
KIND="$1"; VCD="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
export PDK_ROOT="${PDK_ROOT:-/media/pdk}"
OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
if [[ "$KIND" == "core" ]]; then
  DESIGN="${DESIGN:-bmi_snn_top}"
  export RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$DESIGN/runs/$DESIGN}" TOP="$DESIGN" VCD_SCOPE="tb_bmi_snn/u_dut" PERIOD_NS="${PERIOD_NS:-20}" MACRO_INST="${MACRO_INST:-u_wmem}"
  export LIB_SC="$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib"
  export LIB_SRAM="$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80.lib"
else
  export RUN_DIR="${RUN_DIR:-$SKY/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc}" TOP=sky130_vex2_soc VCD_SCOPE="tb_fw_mnist/u_soc" PERIOD_NS="${PERIOD_NS:-20}" MACRO_INST="u_imem u_dmem"
  export LIB_SC="$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_ms/lib/sky130_fd_sc_ms__tt_025C_1v80.lib"
  export LIB_SRAM="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80.lib"
fi
export VCD_FILE="$VCD" OUT="${3:-$ROOT/power/out_vcd_$(basename "$VCD" .vcd)}"
rm -rf "$OUT"; mkdir -p "$OUT"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c sta -no_splash -exit "$ROOT/power/power_vcd_sta.tcl" > "$OUT/sta.log" 2>&1 || { tail -20 "$OUT/sta.log"; exit 1; }
tail -5 "$OUT/sta.log"; grep -A12 "Group" "$OUT/power_vcd.rpt" | head -14
