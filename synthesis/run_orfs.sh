#!/usr/bin/env bash
# Multi-PDK study: harden the hardwired 16-bit H=16 core on an OpenROAD-flow-scripts platform (asap7, nangate45, ihp-sg13g2)
# with the OpenROAD/Yosys binaries of the OpenLane 2 Nix environment. Usage: ./synthesis/run_orfs.sh <platform>
# Expects /media/pdk/OpenROAD-flow-scripts at revision b4dbcb4 (2024-10-02, matches OpenROAD edf00dff of OpenLane 2.3.10):
#   git clone https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts && git -C OpenROAD-flow-scripts checkout b4dbcb4978
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; PLAT="$1"; ORFS="${ORFS:-/media/pdk/OpenROAD-flow-scripts}"; OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
case $PLAT in nangate45) P=nangate45;; ihp-sg13g2) P=ihp;; asap7) P=asap7;; *) echo "platform?"; exit 2;; esac
"$ROOT/.venv/bin/python" "$ROOT/sw/gen_variant.py" --pdk $P bmi_snn_min16 "$ROOT/rtl/h16"
mkdir -p "$ORFS/flow/designs/$PLAT/bmi_snn_min16"; cp "$ROOT/synthesis/orfs/$PLAT/"{config.mk,constraint.sdc} "$ORFS/flow/designs/$PLAT/bmi_snn_min16/"
sed -i "s#^export VERILOG_FILES = .*#export VERILOG_FILES = $ROOT/rtl/gen/pdk/$P/bmi_snn_min16.v#" "$ORFS/flow/designs/$PLAT/bmi_snn_min16/config.mk"
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c bash -c \
  "cd '$ORFS/flow' && make DESIGN_CONFIG=./designs/$PLAT/bmi_snn_min16/config.mk OPENROAD_EXE=\$(which openroad) YOSYS_EXE=\$(which yosys) KLAYOUT_CMD=\$(which klayout)"
NICK=$(sed -n 's/^export DESIGN_NICKNAME *= *\([^ ]*\).*/\1/p' "$ROOT/synthesis/orfs/$PLAT/config.mk"); NICK=${NICK:-bmi_snn_min16}   # results/logs land under the nickname (IHP: bmi_snn_min16_pad2)
ls "$ORFS/flow/results/$PLAT/$NICK/base/" | grep -E "6_final"
