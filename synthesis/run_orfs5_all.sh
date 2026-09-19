#!/usr/bin/env bash
# Round 5 (E5): all cores of the cross-node study on one platform/flavour, in the order of importance, one after the other.
# Usage: synthesis/run_orfs5_all.sh <platform> [flavour] [cores...]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; PLAT="$1"; FLAV="${2:-rvt}"; shift 2 2>/dev/null; CORES="${@:-bmi_snn_sp bmi_snn_m12 bmi_snn_min32 bmi_snn_min16 bmi_snn_lmin2}"
for c in $CORES; do "$ROOT/synthesis/run_orfs5.sh" "$PLAT" "$c" "$FLAV"; done
echo "ALL DONE $PLAT $FLAV $(date)"
