#!/usr/bin/env bash
# Round 10: finish a real-time run whose simulation completed but whose measurement chain was interrupted (sim/build_<tag>/toggles.tsv
# and vvp.log with PASS exist, power/out_<tag>/root_clock_correction.json does not): OpenSTA on the toggles, the zero-data run, the
# root-clock correction, coverage, then sim/rt_post.sh. The simulation wall-clock, if not recorded, is taken from the file times
# (gls.vvp = end of compilation, toggles.tsv = end of the waveform). Usage: rt_finish.sh <design> <tag> [run_tag]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"; TAG="$2"; RUN_TAG="${3:-${D}_5m}"; CLK_NS="${CLK_NS:-200}"
B="$ROOT/sim/build_$TAG"; OUT="$ROOT/power/out_$TAG"; export RUN_DIR="${RUN_DIR:-$ROOT/synthesis/$D/runs/$RUN_TAG}"; NL="$RUN_DIR/final/nl/$D.nl.v"
[[ -f "$B/toggles.tsv" && -f "$B/vvp.log" ]] || { echo "rt_finish: $TAG has no toggles.tsv / vvp.log"; exit 1; }
pgrep -f "vvp -n gls.vvp" > /dev/null && for p in $(pgrep -f "vvp -n gls.vvp"); do [[ "$(readlink /proc/$p/cwd 2>/dev/null)" == "$B" ]] && { echo "rt_finish: simulation of $TAG still running"; exit 1; }; done
grep -q "^PASS" "$B/vvp.log" || { echo "rt_finish: $TAG did not pass"; exit 1; }
rm -f "$B"/*.vcd
grep -q "SIM_WALLCLOCK_S" "$B/vvp.log" || echo "SIM_WALLCLOCK_S $(( $(stat -c %Y "$B/toggles.tsv") - $(stat -c %Y "$B/gls.vvp") ))" >> "$B/vvp.log"
MACRO="none"; export LIB_SRAM="${LIB_SRAM:-/nonexistent}"
[[ "$RUN_TAG" == *_lv ]] && export LIB_SC="${LIB_SC:-/media/pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_n40C_1v28.lib}"   # the 1.28 V re-hardened core is evaluated with its own liberty
case "$D" in bmi_snn_top|bmi_snn_topg) MACRO="u_wmem"; export LIB_SRAM="$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" ;; esac
export UNANNOTATED_ZERO=1
echo "==== finish $TAG ($(date +%H:%M:%S))"
DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN_DIR" "$ROOT/power/run_toggles_power.sh" core "$B/toggles.tsv" "$OUT" > "$ROOT/logs/power_$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/power_$TAG.log"; exit 1; }
GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN_DIR" "$ROOT/power/run_toggles_power.sh" core "$B/toggles.tsv" "${OUT}_zero" > "$ROOT/logs/power_${TAG}_zero.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_zero.log"; exit 1; }
DUTY=$(python3 - "$B/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
python3 "$ROOT/power/root_clock_correction.py" "$NL" clk "$DUTY" "$OUT/power_vcd_by_instance.rpt" "${OUT}_zero/power_vcd_by_instance.rpt" -o "$OUT/root_clock_correction.json" | tail -2
"$ROOT/.venv/bin/python" "$ROOT/sw/annot_coverage.py" "$NL" "$OUT" | tail -1
grep -E "^Total" "$OUT/power_vcd.rpt"
"$ROOT/sim/rt_post.sh" "$D" "$TAG" "$RUN_TAG" || echo "WARNING: rt_post failed for $TAG"
echo "==== finish $TAG done ($(date +%H:%M:%S))"
