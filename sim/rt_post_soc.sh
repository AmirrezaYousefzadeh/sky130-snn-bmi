#!/usr/bin/env bash
# Round 10: post-processing of one real-time SoC run (see sim/rt_post.sh): macro state correction for the two SRAM22 macros and, if
# the gated toggle file exists, the conditional-duty evaluation. Usage: rt_post_soc.sh <variant>  (e.g. _5m_tuned_rt100) [run_dir]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"; V="$1"; CLK_NS="${CLK_NS:-200}"
RUN_DIR="${2:-$SKY/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc_5m}"; TAG="riscv_rt$V"; B="$ROOT/sim/build_$TAG"; OUT="$ROOT/power/out_$TAG"
NL="$RUN_DIR/final/nl/sky130_vex2_soc.nl.v"; LIB="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib"
[[ -f "$OUT/root_clock_correction.json" ]] || { echo "rt_post_soc: $TAG not finished"; exit 1; }
export UNANNOTATED_ZERO=1
run_sta() { local o=$1; shift; env "$@" RUN_DIR="$RUN_DIR" PERIOD_NS=$CLK_NS VCD_SCOPE=tb_fw_bmi_rt/u_soc LIB_SRAM="$LIB" "$ROOT/power/run_toggles_power.sh" riscv "$B/toggles.tsv" "$o" > "$o.log" 2>&1 || { tail -5 "$o.log"; return 1; }; }
if [[ ! -f "$OUT/macro_state_correction.json" ]]; then
  echo "---- $TAG: macro state correction ($(date +%H:%M:%S))"
  python3 "$ROOT/power/macro_state_correction.py" gen "$OUT" "$NL" "$LIB" -o "$OUT/macro_cond.tcl" --json "$OUT/macro_cond.json"
  run_sta "${OUT}_mcond" EXTRA_ACT_TCL="$OUT/macro_cond.tcl"
  python3 "$ROOT/power/macro_state_correction.py" compare "$OUT" "${OUT}_mcond" "$NL" --json "$OUT/macro_state_correction.json"
fi
if [[ -f "$B/toggles_gated.tsv" && ! -f "${OUT}_cond/root_clock_correction.json" ]]; then
  echo "---- $TAG: conditional-duty evaluation ($(date +%H:%M:%S))"
  run_sta "${OUT}_cond" GATED_TSV="$B/toggles_gated.tsv"
  DUTY=$(python3 - "$B/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
  python3 "$ROOT/power/root_clock_correction.py" "$NL" clk "$DUTY" "${OUT}_cond/power_vcd_by_instance.rpt" "${OUT}_zero/power_vcd_by_instance.rpt" -o "${OUT}_cond/root_clock_correction.json" | tail -1
  [[ -f "$OUT/macro_cond.json" ]] && python3 - "$OUT/macro_cond.json" "${OUT}_cond/activity.tcl" <<'PY'
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
echo "---- rt_post_soc $TAG done ($(date +%H:%M:%S))"
