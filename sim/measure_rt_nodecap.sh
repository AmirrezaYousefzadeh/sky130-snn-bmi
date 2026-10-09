#!/usr/bin/env bash
# Round 10 (E10): real-time power of the decap-free refill of a sky130 core. The refilled netlist (synthesis/refill_nodecap.sh) has the
# same logic cells, placement and routing as the measured one and differs only in fill cells without signal pins, so the real-time
# simulation of the refilled netlist is the one already run on the default fill (same stimulus, same cells, same waveform; checked on
# the pruned core with a re-simulation, see the run log). OpenSTA is therefore rerun on the recorded real-time toggles with the refilled
# netlist and its parasitics (annotated run, zero-data run, root-clock correction), and the leakage is split by cell class for both fills.
# Usage: measure_rt_nodecap.sh <design> <rt_tag> [run_tag=<design>_5m]   e.g. bmi_snn_hw rt_bmi_snn_hw_5m_sdf_md0_w5000_indy_20160630_01
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"; TAG="$2"; RT="${3:-${D}_5m}"; CLK_NS="${CLK_NS:-200}"
RUN0="$ROOT/synthesis/$D/runs/$RT"; RUN1="$ROOT/synthesis/$D/runs/${RT}_nodecap"; TSV="$ROOT/sim/build_$TAG/toggles.tsv"; OUT0="$ROOT/power/out_$TAG"; OUT1="$ROOT/power/out_${TAG}_nodecap"
[[ -f "$TSV" ]] || { echo "no toggles $TSV"; exit 1; }; [[ -f "$RUN1/final/nl/$D.nl.v" ]] || { echo "no refilled netlist in $RUN1"; exit 1; }
MACRO=none; export LIB_SRAM="${LIB_SRAM:-/nonexistent}"
case "$D" in bmi_snn_top|bmi_snn_topg) MACRO="u_wmem"; export LIB_SRAM="$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" ;; esac
export UNANNOTATED_ZERO=1
echo "==== nodecap $D ($TAG): OpenSTA on the refilled netlist ($(date +%H:%M:%S))"
DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN1" "$ROOT/power/run_toggles_power.sh" core "$TSV" "$OUT1" > "$ROOT/logs/power_${TAG}_nodecap.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_nodecap.log"; exit 1; }
GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN1" "$ROOT/power/run_toggles_power.sh" core "$TSV" "${OUT1}_zero" > "$ROOT/logs/power_${TAG}_nodecap_zero.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_nodecap_zero.log"; exit 1; }
DUTY=$(python3 - "$ROOT/sim/build_$TAG/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
python3 "$ROOT/power/root_clock_correction.py" "$RUN1/final/nl/$D.nl.v" clk "$DUTY" "$OUT1/power_vcd_by_instance.rpt" "${OUT1}_zero/power_vcd_by_instance.rpt" -o "$OUT1/root_clock_correction.json" | tail -2
"$ROOT/.venv/bin/python" "$ROOT/sw/annot_coverage.py" "$RUN1/final/nl/$D.nl.v" "$OUT1" | tail -1
echo "-- leakage by class, default fill:"; "$ROOT/.venv/bin/python" "$ROOT/sw/leak_classes10.py" "$OUT0/power_vcd_by_instance.rpt" "$RUN0/final/nl/$D.nl.v" -o "$OUT0/leak_classes.json"
echo "-- leakage by class, decap-free fill:"; "$ROOT/.venv/bin/python" "$ROOT/sw/leak_classes10.py" "$OUT1/power_vcd_by_instance.rpt" "$RUN1/final/nl/$D.nl.v" -o "$OUT1/leak_classes.json"
python3 - "$RUN0/final/metrics.json" "$RUN1/final/metrics.json" "$OUT1/refill.json" <<'PY'
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
json.dump(dict(route_drc_errors_original=a.get("route__drc_errors"), route_drc_errors_refill=b.get("refill__route_drc_errors_original"), setup_ws_ns_refill=b.get("timing__setup__ws"), hold_ws_ns_refill=b.get("timing__hold__ws"), setup_ws_ns_default=a.get("timing__setup__ws"), hold_ws_ns_default=a.get("timing__hold__ws"),
               cells_refill=b.get("design__instance__count"), cells_default=a.get("design__instance__count"), note=b.get("refill__note")), open(sys.argv[3], "w"), indent=1)
PY
grep -E "^Total" "$OUT0/power_vcd.rpt" | sed 's/^/default  /'; grep -E "^Total" "$OUT1/power_vcd.rpt" | sed 's/^/nodecap  /'
echo "==== nodecap $D done ($(date +%H:%M:%S))"
