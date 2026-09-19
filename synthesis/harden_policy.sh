#!/usr/bin/env bash
# Round 5 (E1): harden a standard-cell core at the common clock with the utilization policy.
# Usage: synthesis/harden_policy.sh <design> [clock_ns=200] [utilizations="60 50 40 30 20"]
# Writes synthesis/<design>/config_5mhz.yaml from config.yaml (CLOCK_PERIOD, FP_CORE_UTIL, PL_TARGET_DENSITY_PCT=util+10, OpenLane
# default SYNTH_STRATEGY and DRT_OPT_ITERS), runs OpenLane once per utilization (run tag <design>_5m_u<util>) until detailed routing
# converges (route__drc_errors == 0) and timing is met at every signoff corner (RESULT: PASS), then links runs/<design>_5m to that run.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"; CLK="${2:-200}"; UTILS="${3:-60 50 40 30 20}"; B="$(basename "$D")"   # D may be a path (pdk_gf180/<core>, with PDK=gf180mcuD in the environment)
DES="$ROOT/synthesis/$D"; SRC="$DES/config.yaml"; CFG="$DES/config_5mhz.yaml"; LOG="$ROOT/results/run_log_round5.md"
python3 - "$SRC" "$CFG" "$CLK" <<'PY'
import sys, re
src, dst, clk = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
s = re.sub(r"^CLOCK_PERIOD:.*$", f"CLOCK_PERIOD: {clk}", s, flags=re.M)
s = re.sub(r"^SYNTH_STRATEGY:.*\n", "", s, flags=re.M)          # OpenLane default (AREA 0) at the relaxed clock
s = re.sub(r"^DRT_OPT_ITERS:.*\n", "", s, flags=re.M)           # default 64 iterations
s = re.sub(r"^RUN_HEURISTIC_DIODE_INSERTION:.*$", "RUN_HEURISTIC_DIODE_INSERTION: false   # round 5: heuristic diodes broke legalization at 50-60 % utilization; diodes on input ports only", s, flags=re.M)
s = re.sub(r"^(RUN_HEURISTIC_DIODE_INSERTION:.*)$", r"\1\nDIODE_ON_PORTS: in", s, flags=re.M)
s = re.sub(r"^FP_CORE_UTIL:.*$", "FP_CORE_UTIL: @UTIL@", s, flags=re.M)
s = re.sub(r"^PL_TARGET_DENSITY_PCT:.*$", "PL_TARGET_DENSITY_PCT: @DENS@", s, flags=re.M)
s = "# Round-5 configuration (E1): common 5 MHz clock, utilization policy; generated from config.yaml by synthesis/harden_policy.sh\n" + s
open(dst + ".tmpl", "w").write(s)
PY
for U in $UTILS; do
  DENS=$((U + 10)); [ $DENS -gt 95 ] && DENS=95
  sed -e "s/@UTIL@/$U/" -e "s/@DENS@/$DENS/" "$CFG.tmpl" > "$CFG"
  TAG="${B}_5m_u$U"; T0=$(date +%s)
  echo "==== $D: clock $CLK ns, utilization $U % (density $DENS %), run tag $TAG ($(date +%H:%M))"
  DESIGN=$D CFG="$CFG" RUN_TAG=$TAG "$ROOT/synthesis/run_synthesis.sh" > "$ROOT/logs/openlane_$TAG.log" 2>&1
  SR="$DES/runs/$TAG/synthesis_results.txt"; MJ="$DES/runs/$TAG/final/metrics.json"
  DRC=$(python3 -c "import json,sys; m=json.load(open('$MJ')); print(m.get('route__drc_errors','NA'))" 2>/dev/null || echo NA)
  PASS=$(grep -c "RESULT: PASS" "$SR" 2>/dev/null || echo 0)
  DT=$(( ($(date +%s) - T0) / 60 ))
  grep -E "setup slack|hold slack|RESULT" "$SR" 2>/dev/null | sed 's/^/   /'
  echo "   drc_errors=$DRC timing_pass=$PASS runtime=${DT}min"
  if [ "$DRC" = "0" ] && [ "$PASS" = "1" ]; then
    ln -sfn "$TAG" "$DES/runs/${B}_5m"; cp "$CFG" "$DES/config_5mhz_used.yaml"
    echo "   -> accepted: runs/${B}_5m -> $TAG"; echo "$D ACCEPTED util=$U tag=$TAG runtime=${DT}min drc=$DRC" >> "$ROOT/logs/policy_round5.log"; exit 0
  fi
  echo "$D REJECTED util=$U tag=$TAG runtime=${DT}min drc=$DRC pass=$PASS" >> "$ROOT/logs/policy_round5.log"
  [ "$DRC" = "NA" ] && { echo "   run failed before routing metrics (see logs/openlane_$TAG.log)"; tail -n 5 "$ROOT/logs/openlane_$TAG.log"; }
done
echo "$D: no utilization in the policy list converged" | tee -a "$ROOT/logs/policy_round5.log"; exit 1
