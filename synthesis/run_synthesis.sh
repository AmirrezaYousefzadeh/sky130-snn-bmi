#!/usr/bin/env bash
# Harden bmi_snn_top with OpenLane 2.  Usage: RUN_TAG=name ./synthesis/run_synthesis.sh [--full]
set -euo pipefail
export PATH="/nix/var/nix/profiles/default/bin:$PATH"
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null || true
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PDK_ROOT="${PDK_ROOT:-/media/pdk}"; export PDK="${PDK:-sky130A}"
OL2="${OPENLANE_ROOT:-/media/hardware_design_tools/openlane2}"
DESIGN="${DESIGN:-bmi_snn_top}"
DES="$ROOT/synthesis/$DESIGN"; CFG="${CFG:-$DES/config.yaml}"
RUN_TAG="${RUN_TAG:-$DESIGN}"; TO="${TO:-OpenROAD.STAPostPNR}"
[[ "${1:-}" == "--full" ]] && TO=""
EXTRA=(--overwrite); [[ -n "$TO" ]] && EXTRA+=(--to "$TO")
rm -rf "$DES/runs/$RUN_TAG"
cd "$DES"
nix --extra-experimental-features "nix-command flakes" develop --accept-flake-config "$OL2" -c \
  python3 -m openlane --pdk-root "$PDK_ROOT" --pdk "$PDK" --manual-pdk --run-tag "$RUN_TAG" "${EXTRA[@]}" "$CFG"
echo "==== results ===="
python3 "$ROOT/../skywater/synthesis/report_results.py" --design-dir "$DES" --run-tag "$RUN_TAG" --config "$CFG" \
  -o "$DES/runs/$RUN_TAG/synthesis_results.txt" || true
cat "$DES/runs/$RUN_TAG/synthesis_results.txt" 2>/dev/null || true
