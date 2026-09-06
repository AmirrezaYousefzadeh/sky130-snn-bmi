#!/usr/bin/env bash
# Hedge variant: harden <design> from synthesis/<design>_lo (lower utilisation), then measure with RUN_DIR override.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"
DESIGN=${D}_lo "$ROOT/synthesis/run_synthesis.sh" > "$ROOT/logs/openlane_${D}_lo.log" 2>&1
F="$ROOT/synthesis/${D}_lo/runs/${D}_lo/synthesis_results.txt"
grep -E "setup slack|hold slack|critical path|RESULT|total  |stdcells  " "$F"
if grep -q "RESULT: PASS" "$F"; then
  export RUN_DIR="$ROOT/synthesis/${D}_lo/runs/${D}_lo"
  "$ROOT/sim/measure_design.sh" $D func 2>&1 | tail -25
  "$ROOT/sim/measure_design.sh" $D sdf 2>&1 | tail -25
else
  echo "TIMING NOT MET for ${D}_lo - measurement skipped"
fi
