#!/usr/bin/env bash
# Run the BMI SNN software baseline (firmware/) on sky130_vex2_soc: RTL or gate-level (SDF) simulation.
# Usage: ./sim/run_riscv.sh rtl|gls [--vcd]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; SKY="$ROOT/../skywater"; SSIM="$SKY/simulation"
export PATH="/media/hardware_design_tools/oss-cad-suite/bin:$PATH"
PDK_ROOT="${PDK_ROOT:-/media/pdk}"
MODE="$1"; VCD="${2:-}"
RUN_DIR="${RUN_DIR:-$SKY/synthesis/sky130_vex2_soc/runs/sky130_vex2_soc}"
OUT="$ROOT/sim/build_riscv_$MODE"; rm -rf "$OUT"; mkdir -p "$OUT"; cd "$OUT"
make -C "$ROOT/firmware" all >/dev/null
cp -f "$ROOT/firmware/build/imem.hex" "$ROOT/firmware/build/dmem.hex" .
cp -f "$SKY/rtl/cpu/VexRiscv2.v_toplevel_RegFilePlugin_regFile.bin" .
DUMP=(); [[ "$VCD" == "--vcd" ]] && DUMP=(-DDUMP_PATH="\"$OUT/riscv_$MODE.vcd\"" -DDUMP_LEVEL=1 -DDUMP_MODULE=tb_fw_mnist.u_soc)
TIMEOUT=5000000
if [[ "$MODE" == "rtl" ]]; then
  iverilog -g2012 -o fw.vvp -DIMEM_HEX="\"imem.hex\"" -DDMEM_HEX="\"dmem.hex\"" -DTIMEOUT_CYCLES=$TIMEOUT "${DUMP[@]}" \
    "$SKY/rtl/cpu/VexRiscv2.v" "$SKY/rtl/sram/sram22_2048x32m8w8.v" "$SKY/rtl/soc/ibus_sram22_bridge.v" "$SKY/rtl/soc/dbus_sram22_bridge.v" \
    "$SSIM/sky130_dlclkp_stub.v" "$SKY/rtl/soc/clk_gate.v" "$SKY/rtl/soc/sleep_ctrl.v" "$SKY/rtl/soc/sky130_vex2_soc.v" "$SSIM/tb_fw_mnist.v"
  vvp -n fw.vvp | grep -v "^VCD info" | tail -12
else
  LIB=sky130_fd_sc_ms
  NETLIST="$RUN_DIR/final/nl/sky130_vex2_soc.nl.v"
  SDF_SRC="$(find "$RUN_DIR/final/sdf/nom_tt_025C_1v80" -name '*.sdf' | head -1)"
  python3 "$SSIM/sdf_sanitize_for_icarus.py" "$SDF_SRC" -o "$OUT/soc.icarus.sdf"
  python3 "$SSIM/gen_gls_regfile_init.py" -o "$OUT/gls_regfile_init.vh" --scope u_soc
  echo "==> compiling GLS (SoC, $LIB)"
  iverilog -g2012 -gspecify -ginterconnect -Ttyp -o fw_gls.vvp -DGLS_RF_INIT -DGLS_PROGRESS -DUNIT_DELAY='#1' \
    -DSDF_ANNOTATE="\"$OUT/soc.icarus.sdf\"" -DIMEM_HEX="\"imem.hex\"" -DDMEM_HEX="\"dmem.hex\"" -DTIMEOUT_CYCLES=$TIMEOUT "${DUMP[@]}" \
    "$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/primitives.v" "$PDK_ROOT/sky130A/libs.ref/$LIB/verilog/$LIB.v" \
    "$SKY/rtl/sram/sram22_2048x32m8w8.v" "$NETLIST" "$SSIM/tb_fw_mnist.v" 2> iverilog_warn.log || { tail -20 iverilog_warn.log; exit 1; }
  echo "==> running GLS ($(date +%H:%M:%S))"; ( time vvp -n fw_gls.vvp ) > vvp.log 2>&1 || true
  grep -E "PASS|FAIL|TB:|SDF:" vvp.log | head; tail -3 vvp.log
  [[ "$VCD" == "--vcd" ]] && python3 "$SSIM/vcd_rescale_ns.py" "$OUT/riscv_$MODE.vcd" && echo "VCD: $OUT/riscv_$MODE.vcd ($(du -h "$OUT/riscv_$MODE.vcd" | cut -f1))"
fi
