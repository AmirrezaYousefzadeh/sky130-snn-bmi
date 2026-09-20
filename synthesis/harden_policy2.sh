#!/usr/bin/env bash
# Round 5 (E1): utilization policy with a routing watchdog. Same as harden_policy.sh (config_5mhz.yaml from config.yaml: 5 MHz
# clock, FP_CORE_UTIL = U, PL_TARGET_DENSITY_PCT = U + 10, no heuristic diodes), but the OpenLane run is watched: the attempt is
# killed and counted as rejected when detailed routing still has more than 20,000 violations after 3 iterations, more than 3,000
# after 8 iterations, or has not completed an iteration for 3 hours (DRT_OPT_ITERS stays at the default 64 otherwise).
# Usage: synthesis/harden_policy2.sh <design|pdk_gf180/design> [clock_ns=200] [utilizations="60 50 40 30 20"]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"; CLK="${2:-200}"; UTILS="${3:-60 50 40 30 20}"; B="$(basename "$D")"
DES="$ROOT/synthesis/$D"; SRC="$DES/config.yaml"; CFG="$DES/config_5mhz.yaml"
python3 - "$SRC" "$CFG" "$CLK" <<'PY'
import sys, re
src, dst, clk = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
s = re.sub(r"^CLOCK_PERIOD:.*$", f"CLOCK_PERIOD: {clk}", s, flags=re.M)
s = re.sub(r"^SYNTH_STRATEGY:.*\n", "", s, flags=re.M)
s = re.sub(r"^DRT_OPT_ITERS:.*\n", "", s, flags=re.M)
s = re.sub(r"^RUN_HEURISTIC_DIODE_INSERTION:.*$", "RUN_HEURISTIC_DIODE_INSERTION: false   # round 5: heuristic diodes broke legalization at 50-60 % utilization; diodes on input ports only", s, flags=re.M)
s = re.sub(r"^(RUN_HEURISTIC_DIODE_INSERTION:.*)$", r"\1\nDIODE_ON_PORTS: in", s, flags=re.M)
s = re.sub(r"^FP_CORE_UTIL:.*$", "FP_CORE_UTIL: @UTIL@", s, flags=re.M)
s = re.sub(r"^PL_TARGET_DENSITY_PCT:.*$", "PL_TARGET_DENSITY_PCT: @DENS@", s, flags=re.M)
import os
extra = os.environ.get("EXTRA_YAML", "")          # extra configuration lines (e.g. a larger hold-repair margin), appended verbatim
if extra:
    for line in extra.split("\\n"):
        key = line.split(":")[0].strip()
        if key: s = re.sub(r"^" + re.escape(key) + r":.*\n", "", s, flags=re.M)
    s = s.rstrip("\n") + "\n# policy amendment (EXTRA_YAML)\n" + extra.replace("\\n", "\n") + "\n"
s = "# Round-5 configuration (E1): common 5 MHz clock, utilization policy; generated from config.yaml by synthesis/harden_policy2.sh\n" + s
open(dst + ".tmpl", "w").write(s)
PY
watch() { # <run dir> <flow pid>: kill the flow when routing is hopeless; prints the reason. Thresholds WD_VIOL3 (default 20000 after 3
          # iterations) and WD_VIOL8 (3000 after 8) can be raised for the large latch/register-file cores whose routing starts at >200k violations.
  local rd=$1 fp=$2 last_it=-1 last_t=$(date +%s)
  while kill -0 $fp 2>/dev/null; do
    sleep 300
    local log; log=$(ls -t "$rd"/*openroad-detailedrouting*/*.log 2>/dev/null | head -n 1); [[ -z "$log" ]] && { last_t=$(date +%s); continue; }   # the 3 h idle rule counts from the start of detailed routing
    local it viol; it=$(grep -c "Completing 100%" "$log"); viol=$(grep "Number of violations" "$log" | tail -n 1 | awk '{print $NF}' | tr -d .)
    if [[ "$it" != "$last_it" ]]; then last_it=$it; last_t=$(date +%s); fi
    local reason=""
    [[ -n "$viol" && $it -ge 3 && $viol -gt ${WD_VIOL3:-20000} ]] && reason="drt $viol violations after $it iterations"
    [[ -n "$viol" && $it -ge 8 && $viol -gt ${WD_VIOL8:-3000} ]] && reason="drt $viol violations after $it iterations"
    [[ $(( $(date +%s) - last_t )) -gt 10800 ]] && reason="drt no completed iteration for 3 h (at $it)"
    if [[ -n "$reason" ]]; then echo "   WATCHDOG: $reason -> killing the run"; echo "$reason" > "$rd/WATCHDOG_KILLED"; pkill -P $fp; kill $fp 2>/dev/null; sleep 2; pkill -f "runs/$(basename $rd)/" ; return; fi
  done
}
for U in $UTILS; do
  DENS=$((U + 10)); [ $DENS -gt 95 ] && DENS=95
  sed -e "s/@UTIL@/$U/" -e "s/@DENS@/$DENS/" "$CFG.tmpl" > "$CFG"
  TAG="${B}_5m_u$U${TAG_SUFFIX:-}"; T0=$(date +%s)
  echo "==== $D: clock $CLK ns, utilization $U % (density $DENS %), run tag $TAG ($(date +%H:%M))"
  DESIGN=$D CFG="$CFG" RUN_TAG=$TAG "$ROOT/synthesis/run_synthesis.sh" > "$ROOT/logs/openlane_$TAG.log" 2>&1 &
  FP=$!; watch "$DES/runs/$TAG" $FP; wait $FP 2>/dev/null
  SR="$DES/runs/$TAG/synthesis_results.txt"; MJ="$DES/runs/$TAG/final/metrics.json"
  DRC=$(python3 -c "import json,sys; m=json.load(open('$MJ')); print(m.get('route__drc_errors','NA'))" 2>/dev/null || echo NA)
  PASS=$(grep -c "RESULT: PASS" "$SR" 2>/dev/null || true); PASS=${PASS:-0}
  DT=$(( ($(date +%s) - T0) / 60 )); WD=""; [[ -f "$DES/runs/$TAG/WATCHDOG_KILLED" ]] && WD=" watchdog=\"$(cat "$DES/runs/$TAG/WATCHDOG_KILLED")\""
  grep -E "setup slack|hold slack|RESULT" "$SR" 2>/dev/null | sed 's/^/   /'
  echo "   drc_errors=$DRC timing_pass=$PASS runtime=${DT}min$WD"
  if [ "$DRC" = "0" ] && [ "$PASS" = "1" ]; then
    ln -sfn "$TAG" "$DES/runs/${B}_5m"; cp "$CFG" "$DES/config_5mhz_used.yaml"
    echo "   -> accepted: runs/${B}_5m -> $TAG"; echo "$D ACCEPTED util=$U tag=$TAG runtime=${DT}min drc=$DRC" >> "$ROOT/logs/policy_round5.log"; exit 0
  fi
  echo "$D REJECTED util=$U tag=$TAG runtime=${DT}min drc=$DRC pass=$PASS$WD" >> "$ROOT/logs/policy_round5.log"
  [ "$DRC" = "NA" ] && { echo "   run failed before routing metrics (see logs/openlane_$TAG.log)"; tail -n 5 "$ROOT/logs/openlane_$TAG.log"; }
done
echo "$D: no utilization in the policy list converged" | tee -a "$ROOT/logs/policy_round5.log"; exit 1
