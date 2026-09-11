#!/usr/bin/env bash
# Average power of the RISC-V SoC baseline from its gate-level VCD, using the sky130-vex2-soc power flow.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"
VARIANT="${VARIANT:-}"
VCD="${1:-$ROOT/sim/build_riscv_gls${VARIANT}/riscv_gls${VARIANT}.vcd}"
OUT="$ROOT/power/out_riscv${VARIANT}" SCOPE=tb_fw_mnist.u_soc DESIGN_PERIOD_NS=20 "$SKY/power/run_avg_power.sh" "$VCD"
