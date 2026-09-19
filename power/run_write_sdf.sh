#!/usr/bin/env bash
# Round 5 (E5): SDF of a routed netlist from OpenSTA (netlist + SPEF + liberty), for kits whose flow writes no SDF (ASAP7 in ORFS).
# Env: DESIGN RUN_DIR LIB_SC NETLIST SPEF PERIOD_NS SDF_OUT
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
export TOP="$DESIGN" OUT="$(dirname "$SDF_OUT")"; mkdir -p "$OUT"
export PATH="/nix/var/nix/profiles/default/bin:$PATH"; source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c sta -no_splash -exit "$ROOT/power/write_sdf_sta.tcl"
ls -la "$SDF_OUT"
