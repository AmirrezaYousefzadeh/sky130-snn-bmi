#!/usr/bin/env bash
# Round 10 (E10): decap-free refill of the RISC-V SoC measured on the recorded real-time toggles (see sim/measure_rt_nodecap.sh).
# Usage: measure_rt_nodecap_soc.sh <variant>   e.g. _5m_tuned_rt100  -> power/out_riscv_rt<variant>_nodecap
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"; V="$1"; CLK_NS="${CLK_NS:-200}"
TAG="riscv_rt$V"; TSV="$ROOT/sim/build_$TAG/toggles.tsv"; RUN0="$SKY/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc_5m"; RUN1="${RUN0}_nodecap"
OUT0="$ROOT/power/out_$TAG"; OUT1="$ROOT/power/out_${TAG}_nodecap"; LIB="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib"
[[ -f "$TSV" && -f "$RUN1/final/nl/sky130_vex2_soc.nl.v" ]] || { echo "missing toggles or refilled SoC netlist"; exit 1; }
export UNANNOTATED_ZERO=1
echo "==== nodecap SoC ($TAG): OpenSTA on the refilled netlist ($(date +%H:%M:%S))"
RUN_DIR="$RUN1" PERIOD_NS=$CLK_NS VCD_SCOPE=tb_fw_bmi_rt/u_soc LIB_SRAM="$LIB" "$ROOT/power/run_toggles_power.sh" riscv "$TSV" "$OUT1" > "$ROOT/logs/power_${TAG}_nodecap.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_nodecap.log"; exit 1; }
GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 RUN_DIR="$RUN1" PERIOD_NS=$CLK_NS VCD_SCOPE=tb_fw_bmi_rt/u_soc LIB_SRAM="$LIB" "$ROOT/power/run_toggles_power.sh" riscv "$TSV" "${OUT1}_zero" > "$ROOT/logs/power_${TAG}_nodecap_zero.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_nodecap_zero.log"; exit 1; }
DUTY=$(python3 - "$ROOT/sim/build_$TAG/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
python3 "$ROOT/power/root_clock_correction.py" "$RUN1/final/nl/sky130_vex2_soc.nl.v" clk "$DUTY" "$OUT1/power_vcd_by_instance.rpt" "${OUT1}_zero/power_vcd_by_instance.rpt" -o "$OUT1/root_clock_correction.json" | tail -2
"$ROOT/.venv/bin/python" "$ROOT/sw/annot_coverage.py" "$RUN1/final/nl/sky130_vex2_soc.nl.v" "$OUT1" | tail -1
echo "-- leakage by class, default fill:"; "$ROOT/.venv/bin/python" "$ROOT/sw/leak_classes10.py" "$OUT0/power_vcd_by_instance.rpt" "$RUN0/final/nl/sky130_vex2_soc.nl.v" -o "$OUT0/leak_classes.json"
echo "-- leakage by class, decap-free fill:"; "$ROOT/.venv/bin/python" "$ROOT/sw/leak_classes10.py" "$OUT1/power_vcd_by_instance.rpt" "$RUN1/final/nl/sky130_vex2_soc.nl.v" -o "$OUT1/leak_classes.json"
python3 - "$RUN0/final/metrics.json" "$RUN1/final/metrics.json" "$OUT1/refill.json" <<'PY'
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
json.dump(dict(route_drc_errors_original=a.get("route__drc_errors"), route_drc_errors_refill=b.get("refill__route_drc_errors_original"), setup_ws_ns_refill=b.get("timing__setup__ws"), hold_ws_ns_refill=b.get("timing__hold__ws"), setup_ws_ns_default=a.get("timing__setup__ws"), hold_ws_ns_default=a.get("timing__hold__ws"), cells_refill=b.get("design__instance__count"), cells_default=a.get("design__instance__count"), note=b.get("refill__note")), open(sys.argv[3], "w"), indent=1)
PY
grep -E "^Total" "$OUT0/power_vcd.rpt" | sed 's/^/default  /'; grep -E "^Total" "$OUT1/power_vcd.rpt" | sed 's/^/nodecap  /'; echo "==== nodecap SoC done ($(date +%H:%M:%S))"
