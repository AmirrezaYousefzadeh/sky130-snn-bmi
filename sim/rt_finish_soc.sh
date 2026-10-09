#!/usr/bin/env bash
# Round 10: finish a real-time SoC run whose power chain did not run (e.g. the testbench reported overruns): OpenSTA on the toggles,
# zero run, root-clock correction, coverage, post-processing. Usage: rt_finish_soc.sh <variant>   (e.g. _5m_o2_rt100)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"; V="$1"; CLK_NS="${CLK_NS:-200}"
RUN_DIR="${RUN_DIR:-$SKY/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc_5m}"; TAG="riscv_rt$V"; OUT="$ROOT/sim/build_$TAG"; POUT="$ROOT/power/out_$TAG"
NETLIST="$RUN_DIR/final/nl/sky130_vex2_soc.nl.v"; LIB="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib"
[[ -f "$OUT/toggles.tsv" ]] || { echo "no toggles for $TAG"; exit 1; }
rm -f "$OUT"/*.vcd; export UNANNOTATED_ZERO=1
echo "==== finish SoC $TAG ($(date +%H:%M:%S)): $(grep -E '^(PASS|FAIL)' $OUT/vvp.log | head -1)"
RUN_DIR="$RUN_DIR" PERIOD_NS=$CLK_NS VCD_SCOPE=tb_fw_bmi_rt/u_soc LIB_SRAM="$LIB" "$ROOT/power/run_toggles_power.sh" riscv "$OUT/toggles.tsv" "$POUT" > "$ROOT/logs/power_$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/power_$TAG.log"; exit 1; }
GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 RUN_DIR="$RUN_DIR" PERIOD_NS=$CLK_NS VCD_SCOPE=tb_fw_bmi_rt/u_soc LIB_SRAM="$LIB" "$ROOT/power/run_toggles_power.sh" riscv "$OUT/toggles.tsv" "${POUT}_zero" > "$ROOT/logs/power_${TAG}_zero.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_zero.log"; exit 1; }
DUTY=$(python3 - "$OUT/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
python3 "$ROOT/power/root_clock_correction.py" "$NETLIST" clk "$DUTY" "$POUT/power_vcd_by_instance.rpt" "${POUT}_zero/power_vcd_by_instance.rpt" -o "$POUT/root_clock_correction.json" | tail -2
"$ROOT/.venv/bin/python" "$ROOT/sw/annot_coverage.py" "$NETLIST" "$POUT" | tail -1
grep -E "^Total" "$POUT/power_vcd.rpt"
"$ROOT/sim/rt_post_soc.sh" "$V" || echo "WARNING: rt_post_soc failed"
echo "==== finish SoC $TAG done ($(date +%H:%M:%S))"
