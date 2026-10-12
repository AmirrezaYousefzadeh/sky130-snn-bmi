#!/usr/bin/env bash
# Round 10 (E6): real-time gate-level run of the RISC-V SoC software decoder (sim/tb_fw_bmi_rt.v: one wake per 4 ms bin, the external
# clock stopped while the SoC sleeps) with the waveform streamed into tools/vcd_toggles, then per-pin OpenSTA power over the whole
# window (power/run_toggles_power.sh riscv), a zero-data run for the root-clock correction, and the correction itself.
# Usage: FW_SRC=bmi_snn_sw_tuned_rt.c FW_OPT=-O2 VARIANT=_5m_tuned_rt100 ./sim/run_riscv_rt.sh [rtl|gls]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"; SSIM="$SKY/simulation"
export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"; PDK_ROOT="${PDK_ROOT:-/media/pdk}"
MODE="${1:-gls}"; VARIANT="${VARIANT:-_5m_rt}"; NB="${NB:-100}"; CLK_NS="${CLK_NS:-200}"
RUN_DIR="${RUN_DIR:-$SKY/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc_5m}"
TAG="riscv_rt${VARIANT}"; OUT="$ROOT/sim/build_$TAG"; rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
make -C "$ROOT/firmware" all OPT="${FW_OPT:--O2}" SRC="${FW_SRC:-bmi_snn_sw_rt.c}" > "$OUT/make.log" 2>&1 || { tail -5 "$OUT/make.log"; exit 1; }
cp -f "$ROOT/firmware/build/imem.hex" "$ROOT/firmware/build/dmem.hex" .; cp -f "$SKY/rtl/cpu/VexRiscv2.v_toplevel_RegFilePlugin_regFile.bin" .
COMMON=(-DIMEM_HEX="\"imem.hex\"" -DDMEM_HEX="\"dmem.hex\"" -DN_BINS=$NB -DCLK_PERIOD_NS=$CLK_NS -DTIMEOUT_CYCLES=50000000 ${EXTRA_DEFS:-})
T0=$(date +%s)
if [[ "$MODE" == "rtl" ]]; then
  iverilog -g2012 -o fw.vvp "${COMMON[@]}" "$SKY/rtl/cpu/VexRiscv2.v" "$SKY/rtl/sram/sram22_2048x32m8w8.v" "$SKY/rtl/soc/ibus_sram22_bridge.v" "$SKY/rtl/soc/dbus_sram22_bridge.v" \
    "$SSIM/sky130_dlclkp_stub.v" "$SKY/rtl/soc/clk_gate.v" "$SKY/rtl/soc/sleep_ctrl.v" "$SKY/rtl/soc/sky130_vex2_soc.v" "$ROOT/sim/tb_fw_bmi_rt.v" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
  ( time vvp -n fw.vvp ) > vvp.log 2>&1 || true; grep -E "PASS|FAIL|RT:|TB:|WARNING|real" vvp.log | head -20; exit 0
fi
LIB=sky130_fd_sc_ms; NETLIST="$RUN_DIR/final/nl/sky130_vex2_soc.nl.v"
SDF_SRC="$(find "$RUN_DIR/final/sdf/nom_tt_025C_1v80" -name '*.sdf' | head -1)"
python3 "$SSIM/sdf_sanitize_for_icarus.py" "$SDF_SRC" -o "$OUT/soc.icarus.sdf"
python3 "$SSIM/gen_gls_regfile_init.py" -o "$OUT/gls_regfile_init.vh" --scope u_soc
FIFO="$OUT/$TAG.vcd"; mkfifo "$FIFO"
echo "==> compiling GLS (SoC, $LIB, real time)"
iverilog -g2012 -gspecify -ginterconnect -Ttyp -o fw_gls.vvp -DGLS_RF_INIT -DGLS_PROGRESS -DUNIT_DELAY='#1' "${COMMON[@]}" \
  -DSDF_ANNOTATE="\"$OUT/soc.icarus.sdf\"" -DDUMP_PATH="\"$FIFO\"" -DDUMP_LEVEL=1 -DDUMP_MODULE=tb_fw_bmi_rt.u_soc \
  "$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/primitives.v" "$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/$LIB.v" \
  "$SKY/rtl/sram/sram22_2048x32m8w8.v" "$NETLIST" "$ROOT/sim/tb_fw_bmi_rt.v" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
GATEOPT=(); [[ -n "${TOGGLE_GATE-tb_fw_bmi_rt/u_soc/sram_clk_en}" ]] && GATEOPT=(--gate "${TOGGLE_GATE-tb_fw_bmi_rt/u_soc/sram_clk_en}" -g "$OUT/toggles_gated.tsv")   # round 10: state duties of the awake cycles
"$ROOT/tools/vcd_toggles" -o "$OUT/toggles.tsv" "${GATEOPT[@]}" "$FIFO" 2> toggles.log & TPID=$!
echo "==> running GLS ($(date +%H:%M:%S)), toggles accumulated by pid $TPID"; ( time vvp -n fw_gls.vvp ) > vvp.log 2>&1 || true
wait $TPID; rm -f "$FIFO"
grep -E "PASS|FAIL|RT:|TB:|WARNING|SDF:|real" vvp.log | head -20; cat toggles.log
echo "SIM_WALLCLOCK_S $(( $(date +%s) - T0 ))" >> vvp.log
grep -q "^PASS" vvp.log || { echo "simulation did not pass"; exit 1; }
POUT="$ROOT/power/out_$TAG"; export UNANNOTATED_ZERO=1
RUN_DIR="$RUN_DIR" PERIOD_NS=$CLK_NS VCD_SCOPE=tb_fw_bmi_rt/u_soc LIB_SRAM="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" \
  "$ROOT/power/run_toggles_power.sh" riscv "$OUT/toggles.tsv" "$POUT" > "$ROOT/logs/power_$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/power_$TAG.log"; exit 1; }
GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 RUN_DIR="$RUN_DIR" PERIOD_NS=$CLK_NS VCD_SCOPE=tb_fw_bmi_rt/u_soc LIB_SRAM="$SKY/synthesis/sky130_vex2_soc/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" \
  "$ROOT/power/run_toggles_power.sh" riscv "$OUT/toggles.tsv" "${POUT}_zero" > "$ROOT/logs/power_${TAG}_zero.log" 2>&1 || { tail -5 "$ROOT/logs/power_${TAG}_zero.log"; exit 1; }
DUTY=$(python3 - "$OUT/vvp.log" "$CLK_NS" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * float(sys.argv[2]) / int(m.group(3)))
PY
)
python3 "$ROOT/power/root_clock_correction.py" "$NETLIST" clk "$DUTY" "$POUT/power_vcd_by_instance.rpt" "${POUT}_zero/power_vcd_by_instance.rpt" -o "$POUT/root_clock_correction.json" | tail -5
grep -E "^Total" "$POUT/power_vcd.rpt"
echo "==== $TAG done ($(date +%H:%M:%S), $(( ($(date +%s) - T0) / 60 )) min)"
