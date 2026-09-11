#!/usr/bin/env bash
# Multi-PDK study: functional gate-level energy of the hardwired 16-bit H=16 core hardened on another PDK.
# Usage: ./sim/measure_pdk.sh gf180|ihp|asap7|nangate45      (gf180 from OpenLane, the others from OpenROAD-flow-scripts)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; P="$1"; D=bmi_snn_min16; ORFS=/media/pdk/OpenROAD-flow-scripts/flow; PDK=/media/pdk
case $P in
  gf180) RUN=$ROOT/synthesis/pdk_gf180/$D/runs/$D; NL=$RUN/final/nl/$D.nl.v; SPEF=$RUN/final/spef/nom/$D.nom.spef
         LIB="$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib"
         VLOG="$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v $PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/gf180mcu_fd_sc_mcu7t5v0.v" ;;
  nangate45) RUN=$ORFS/results/nangate45/$D/base; NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$ORFS/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"; VLOG="/media/pdk/nangate45_models.v" ;;   # functional models generated from the liberty (sim/liberty2verilog.py)
  ihp)   RUN=$ORFS/results/ihp-sg13g2/$D/base; NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$ORFS/platforms/ihp-sg13g2/lib/sg13g2_stdcell_typ_1p20V_25C.lib"
         VLOG="$PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_udp.v $PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v" ;;
  asap7) RUN=$ORFS/results/asap7/$D/base; NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef; PERIOD_LIB=20000   # ASAP7 liberty time unit: ps
         LIB="$(ls $ORFS/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_TT_nldm_*.lib* | tr '\n' ' ')"
         VLOG="$(ls /media/pdk/asap7sc7p5t_28/Verilog/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_RVT_TT_*.v | tr "\n" " ")" ;;
  *) echo "unknown pdk $P"; exit 2 ;;
esac
[ -f "$NL" ] || { echo "no netlist $NL"; exit 1; }; [ -f "$SPEF" ] || echo "WARNING: no SPEF $SPEF (power without parasitics)"
VEC=$ROOT/sim/vec_h16_indy_20160630_01
PERIOD_LIB="${PERIOD_LIB:-20}"     # create_clock period in the liberty's time unit (ns for all libraries but ASAP7)
STUBS=$ROOT/sim/build_pdk_${P}_stubs.v; mkdir -p $(dirname $STUBS); $ROOT/.venv/bin/python $ROOT/sim/gen_phys_stubs.py "$NL" "$STUBS" $VLOG; VLOG="$VLOG $STUBS"
run_one() { local tag=$1 nb=$2 gap=$3
  echo "==== $P $tag ($(date +%H:%M:%S))"
  PDK_VERILOG="$VLOG" INCDIR=$ROOT/rtl/h16 DESIGN=$D DUT=$D NETLIST=$NL TAG=$tag DUMP_LEVEL=0 CLK_NS=20 $ROOT/sim/run_gls_pdk.sh $VEC $nb 0 $gap > $ROOT/logs/$tag.log 2>&1 || { tail -5 $ROOT/logs/$tag.log; return 1; }
  grep -E "SUMMARY|MEASURED|PASS|FAIL" $ROOT/logs/$tag.log | head -3
  DESIGN=$D MACRO_INST=none PERIOD_NS=$PERIOD_LIB RUN_DIR=$RUN LIB_SC="$LIB" NETLIST=$NL SPEF=$SPEF $ROOT/power/run_vcd_power.sh core $ROOT/sim/build_$tag/$tag.vcd > $ROOT/logs/vcd_power_$tag.log 2>&1 || { tail -5 $ROOT/logs/vcd_power_$tag.log; return 1; }
  grep -E "^Total" $ROOT/power/out_vcd_$tag/power_vcd.rpt | head -1
}
run_one pdk_${P}_min16_md0_full 500 0
run_one pdk_${P}_min16_idle_full 1 400000
echo "==== $P done ($(date +%H:%M:%S))"
