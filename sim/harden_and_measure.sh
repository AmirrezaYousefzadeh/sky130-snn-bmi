#!/usr/bin/env bash
# Harden one design, then (only if timing is met at all corners) run its functional and SDF measurement sets.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"
DESIGN=$D "$ROOT/synthesis/run_synthesis.sh" > "$ROOT/logs/openlane_$D.log" 2>&1
F="$ROOT/synthesis/$D/runs/$D/synthesis_results.txt"
grep -E "setup slack|hold slack|critical path|RESULT|total  |stdcells  " "$F"
if grep -q "RESULT: PASS" "$F"; then
  "$ROOT/sim/measure_design.sh" $D func 2>&1 | tail -25
  "$ROOT/sim/measure_design.sh" $D sdf 2>&1 | tail -25
else
  echo "TIMING NOT MET for $D - measurement skipped"
fi
