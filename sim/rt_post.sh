#!/usr/bin/env bash
# Round 10: post-processing of one real-time run (sim/build_<tag>/toggles.tsv, power/out_<tag>/ with the zero run and the root-clock
# correction already present):
#   (1) macro state correction (designs with the SRAM22 macro): second OpenSTA run with the macro control pins (ce, we) at the duty
#       conditioned on the macro clock running -> power/out_<tag>_mcond, power/out_<tag>/macro_state_correction.json
#   (2) conditional-duty evaluation (runs whose toggle file has the gated companion toggles_gated.tsv): OpenSTA with every duty
#       conditioned on the clock enable -> power/out_<tag>_cond (+ its root-clock correction json)
# Usage: rt_post.sh <design> <tag> [run_tag]      (kits: KIT=<gf180|ihp|nangate45|asap7|asap7sram> with NETLIST/SPEF/LIB_SC/PERIOD_NS/LIB_TIME_UNIT_S preset)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"; TAG="$2"; RUN_TAG="${3:-${D}_5m}"; CLK_NS="${CLK_NS:-200}"
B="$ROOT/sim/build_$TAG"; OUT="$ROOT/power/out_$TAG"; [[ -f "$OUT/root_clock_correction.json" ]] || { echo "rt_post: $TAG has no root_clock_correction.json"; exit 1; }
export UNANNOTATED_ZERO=1 RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$D/runs/$RUN_TAG}"
NL="${NETLIST:-$RUN_DIR/final/nl/$D.nl.v}"; MACRO="${MACRO_INST:-none}"; PER="${PERIOD_NS:-$CLK_NS}"
case "$D" in bmi_snn_top|bmi_snn_topg) MACRO="u_wmem"; export LIB_SRAM="${LIB_SRAM:-$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib}" ;; esac
DUTY=$(python3 - "$B/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
run_sta() { # <out_dir> [extra env assignments...]
  local o=$1; shift
  env "$@" DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$PER RUN_DIR="$RUN_DIR" "$ROOT/power/run_toggles_power.sh" core "$B/toggles.tsv" "$o" > "$o.log" 2>&1 || { tail -5 "$o.log"; return 1; }
}
if [[ "$MACRO" != none && ! -f "$OUT/macro_state_correction.json" ]]; then
  echo "---- $TAG: macro state correction ($(date +%H:%M:%S))"
  python3 "$ROOT/power/macro_state_correction.py" gen "$OUT" "$NL" "$LIB_SRAM" -o "$OUT/macro_cond.tcl" --json "$OUT/macro_cond.json"
  run_sta "${OUT}_mcond" EXTRA_ACT_TCL="$OUT/macro_cond.tcl"
  python3 "$ROOT/power/macro_state_correction.py" compare "$OUT" "${OUT}_mcond" "$NL" --json "$OUT/macro_state_correction.json"
fi
if [[ -f "$B/toggles_gated.tsv" && ! -f "${OUT}_cond/root_clock_correction.json" ]]; then
  echo "---- $TAG: conditional-duty evaluation ($(date +%H:%M:%S))"
  run_sta "${OUT}_cond" GATED_TSV="$B/toggles_gated.tsv"
  grep -E "^# duties" "${OUT}_cond/activity.tcl"
  python3 "$ROOT/power/root_clock_correction.py" "$NL" ${CLK_PORT:-clk} "$DUTY" "${OUT}_cond/power_vcd_by_instance.rpt" "${OUT}_zero/power_vcd_by_instance.rpt" -o "${OUT}_cond/root_clock_correction.json" | tail -1
  if [[ "$MACRO" != none && -f "$OUT/macro_cond.json" ]]; then     # the macro's conditional duties measured directly (gated accounting) next to the inferred ones
    python3 - "$OUT/macro_cond.json" "${OUT}_cond/activity.tcl" <<'PY'
import json, re, sys
inf = json.load(open(sys.argv[1])); act = {}
for line in open(sys.argv[2], errors="ignore"):
    m = re.match(r"__(?:top|pin)_act \{(.+?)\} (\S+) (\S+)", line)
    if m: act[m.group(1)] = float(m.group(3))
for inst, rec in inf.items():
    for pin, v in rec["pins"].items():
        meas = act.get(f"{inst}/{pin}", act.get(v["net"]))
        print(f"   {inst}/{pin}: inferred conditional duty {v['duty_conditional']:.6f}, measured (gated) {meas if meas is None else round(meas, 6)}")
PY
  fi
  echo "standard  $(grep -E '^Total' "$OUT/power_vcd.rpt")"; echo "cond-duty $(grep -E '^Total' "${OUT}_cond/power_vcd.rpt")"
fi
echo "---- rt_post $TAG done ($(date +%H:%M:%S))"
