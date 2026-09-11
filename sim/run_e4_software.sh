#!/usr/bin/env bash
# E4: gate-level (SDF) runs of the software baseline variants on the sky130_vex2_soc netlist, power and cycle accounting.
cd "$(dirname "$0")/.."
for v in "_o3 -O3 bmi_snn_sw.c" "_tuned -O3 bmi_snn_sw_tuned.c"; do set -- $v
  echo "==== variant $1 ($2 $3) $(date +%H:%M)"
  VARIANT=$1 FW_OPT="$2" FW_SRC=$3 sim/run_riscv.sh gls --vcd > logs/riscv_gls$1.log 2>&1; grep -E "PASS|FAIL" logs/riscv_gls$1.log | head -2
  VARIANT=$1 power/run_riscv_power.sh > logs/riscv_power$1.log 2>&1; tail -2 logs/riscv_power$1.log | cut -c1-120
  .venv/bin/python sw/riscv_cycles_fast.py sim/build_riscv_gls$1/riscv_gls$1.vcd 16 > results/riscv_cycles$1.json 2> logs/riscv_cycles$1.log; grep -E "cycles_per_bin|decode_cycles" results/riscv_cycles$1.json | head -2
done
echo "E4 DONE $(date)"
