#!/usr/bin/env bash
# Round 5 (E5): energy of a core hardened on another kit at 5 MHz with the utilization policy (synthesis/run_orfs5*.sh, harden_policy.sh).
# Usage: sim/measure_pdk5.sh <gf180|ihp|nangate45|asap7|asap7sram> <sp|m12|min32|min16|lmin2> [func|sdf|volt|all]
#   func: zero-delay GLS, 500-bin window of indy_20160630_01 back-to-back + idle run (1 bin + 400k idle cycles), streamed toggles,
#         per-pin OpenSTA power at the kit's typical liberty          -> sim/build_pdk5_<kit>_<core>_{md0,idle}_full, power/out_vcd_<tag>
#   sdf : annotated GLS of 200 bins (GF180: OpenLane SDF; ASAP7: SDF written by OpenSTA from the routed netlist and its parasitics;
#         IHP and NanGate45 have no timing models for Icarus)          -> ..._md0_sdf
#   volt: the recorded activity re-evaluated with the kit's lowest characterized supply liberty (and intermediate ones), with the
#         worst setup slack at 200 ns                                  -> power/out_vcd_<tag>_<corner>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; P="$1"; C="$2"; KIND="${3:-all}"; D=bmi_snn_$C; ORFS=/media/pdk/OpenROAD-flow-scripts/flow; PDK=/media/pdk
case $C in
  sp)    VP=sp_;  INC=$ROOT/rtl/sp;  LOAD="" ;;
  m12)   VP=v12_; INC=$ROOT/rtl;     LOAD="" ;;
  min32) VP=h32_; INC=$ROOT/rtl/h32; LOAD="" ;;
  min16) VP=h16_; INC=$ROOT/rtl/h16; LOAD="" ;;
  lmin2) VP=v12_; INC=$ROOT/rtl;     LOAD="-DLOAD_PORT -DDUMP_AFTER_LOAD -DHAS_WR_READY" ;;
  *) echo "unknown core $C"; exit 2 ;;
esac
TU=1e-9; PERIOD_LIB=200; SDF_SRC=""; LOWV=(); VLOG_SDF=""; SDF_FUNC=""
case $P in
  gf180) RUN=$ROOT/synthesis/pdk_gf180/$D/runs/${D}_5m; NL=$RUN/final/nl/$D.nl.v; SPEF=$RUN/final/spef/nom/$D.nom.spef
         LIBDIR=$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib; LIB="$LIBDIR/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib"
         VLOG="$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v $PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/gf180mcu_fd_sc_mcu7t5v0.v"
         SDF_SRC="$(find $RUN/final/sdf/nom_tt_025C_5v00 -name '*.sdf' 2>/dev/null | head -1)"
         # annotated runs: vendor timing bodies with the notifier initialized (Icarus has no timing checks); the models must be compiled after a
         # `timescale directive (sim/timescale_1ns_1ps.v, run_gls_stream.sh), otherwise the clock buffers resolve to X under -gspecify
         VLOG_SDF="$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v /media/pdk/icarus_sdf_models/gf180mcu_fd_sc_mcu7t5v0_sdf.v"; SDF_FUNC=""
         LOWV=("tt_025C_3v30:$LIBDIR/gf180mcu_fd_sc_mcu7t5v0__tt_025C_3v30.lib" "tt_025C_1v80:$LIBDIR/gf180mcu_fd_sc_mcu7t5v0__tt_025C_1v80.lib" "ss_125C_1v62:$LIBDIR/gf180mcu_fd_sc_mcu7t5v0__ss_125C_1v62.lib") ;;
  nangate45) RUN=$ORFS/results/nangate45/${D}_5m/base; NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$ORFS/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"; VLOG="/media/pdk/nangate45_models.v" ;;   # only the typical liberty is characterized
  ihp)   RUN=$ORFS/results/ihp-sg13g2/${D}_5m/base; NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$ORFS/platforms/ihp-sg13g2/lib/sg13g2_stdcell_typ_1p20V_25C.lib"; VLOG="/media/pdk/ihp_sg13g2_models_functional.v"
         LOWV=("slow_1p08V_125C:$ORFS/platforms/ihp-sg13g2/lib/sg13g2_stdcell_slow_1p08V_125C.lib") ;;
  asap7|asap7sram) TU=1e-12; PERIOD_LIB=200000
         if [[ $P == asap7 ]]; then FL=RVT; RUN=$ORFS/results/asap7/${D}_5m/base; else FL=SRAM; RUN=$ORFS/results/asap7/${D}_5m_sram/base; fi
         NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$(ls $ORFS/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_${FL}_TT_nldm_*.lib* | tr '\n' ' ')"
         VLOG="$(ls /media/pdk/asap7sc7p5t_28/Verilog/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_${FL}_TT_*.v | tr '\n' ' ')"
         LOWV=("SS:$(ls $ORFS/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_${FL}_SS_nldm_*.lib* | tr '\n' ' ')")
         # annotated runs: vendor combinational models + behavioural sequential cells with matching specify paths (sim/asap7_seq_icarus.v;
         # the vendor UDP-based flip-flops stay X under Icarus without timing checks)
         VLOG_SDF="$(ls /media/pdk/asap7sc7p5t_28/Verilog/asap7sc7p5t_{AO,INVBUF,OA,SIMPLE}_${FL}_TT_*.v | tr '\n' ' ') $ROOT/sim/asap7_seq_icarus.v" ;;
  *) echo "unknown kit $P"; exit 2 ;;
esac
[[ -f "$NL" ]] || { echo "no netlist $NL"; exit 1; }; [[ -f "$SPEF" ]] || echo "WARNING: no SPEF $SPEF (power without parasitics)"
VEC=$ROOT/sim/vec_${VP}indy_20160630_01; [[ -d $VEC ]] || { echo "no vectors $VEC"; exit 1; }
STUBS=$ROOT/sim/build_pdk5_${P}_${C}_stubs.v; mkdir -p "$(dirname "$STUBS")"; $ROOT/.venv/bin/python $ROOT/sim/gen_phys_stubs.py "$NL" "$STUBS" $VLOG; VLOG="$VLOG $STUBS"
export CLK_STOP_ICG="${CLK_STOP_ICG:-1}"      # gated clock subtrees annotated from the waveform (see power/power_toggles_sta.tcl)
sta_run() { # <toggles.tsv> <out_dir> <liberty list>
  DESIGN=$D MACRO_INST=none PERIOD_NS=$PERIOD_LIB LIB_TIME_UNIT_S=$TU RUN_DIR=$RUN LIB_SC="$3" LIB_SRAM=/nonexistent NETLIST=$NL SPEF=$SPEF \
    $ROOT/power/run_toggles_power.sh core "$1" "$2" > "$2.log" 2>&1 || { tail -5 "$2.log"; return 1; }
  grep -E "^Total|WORST_SETUP" "$2/power_vcd.rpt" "$2/sta.log" | head -2
}
sim_run() { # <tag> <nbins> <gap> <sdf|nosdf>
  local tag=$1 nb=$2 gap=$3 extra=""; [[ $4 == nosdf ]] && extra="--no-sdf"
  echo "==== $P $C $tag ($(date +%H:%M:%S))"
  local models="$VLOG" sf=""; [[ $4 == sdf && -n "$VLOG_SDF" ]] && { models="$VLOG_SDF $STUBS"; sf="$SDF_FUNC"; }
  PDK_VERILOG="$models" SDF_FUNCTIONAL="$sf" INCDIR=$INC DESIGN=$D DUT=$D LOAD="$LOAD" NETLIST=$NL RUN_DIR=$RUN SDF_SRC="$SDF_SRC" TAG=$tag DUMP_LEVEL=0 CLK_NS=200 \
    EXTRA_DEFS="-DTIMEOUT_CYCLES=2000000000" timeout ${SIM_TIMEOUT:-4h} $ROOT/sim/run_gls_stream.sh $VEC $nb 0 $gap $extra > $ROOT/logs/$tag.log 2>&1 || { tail -5 $ROOT/logs/$tag.log; return 1; }
  grep -q "^SUMMARY" $ROOT/sim/build_$tag/vvp.log || { echo "   no SUMMARY (simulation did not finish within ${SIM_TIMEOUT:-4h})"; rm -rf $ROOT/sim/build_$tag; return 1; }
  grep -E "SUMMARY|PASS|FAIL|SDF:" $ROOT/logs/$tag.log | head -3
  sta_run $ROOT/sim/build_$tag/toggles.tsv $ROOT/power/out_vcd_$tag "$LIB"
}
T0=pdk5_${P}_${C}
if [[ $KIND == func || $KIND == all ]]; then sim_run ${T0}_md0_full 500 0 nosdf; sim_run ${T0}_idle_full 1 400000 nosdf; fi
if [[ $KIND == sdf || $KIND == all ]]; then
  export SIM_TIMEOUT="${SDF_TIMEOUT:-3h}"     # the annotated ASAP7 vendor models did not progress in Icarus (0 bins in 7 h): bounded
  if [[ $P == asap7 || $P == asap7sram ]]; then   # SDF from OpenSTA on the routed netlist and parasitics (ASAP7 has no flow-written SDF)
    SDF_SRC=$ROOT/sim/build_${T0}_sdf_src/design.sdf; mkdir -p "$(dirname $SDF_SRC)"
    DESIGN=$D RUN_DIR=$RUN LIB_SC="$LIB" NETLIST=$NL SPEF=$SPEF PERIOD_NS=$PERIOD_LIB SDF_OUT=$SDF_SRC $ROOT/power/run_write_sdf.sh > "$(dirname $SDF_SRC)/write_sdf.log" 2>&1 || tail -3 "$(dirname $SDF_SRC)/write_sdf.log"
  fi
  if [[ -f "$SDF_SRC" ]]; then sim_run ${T0}_md0_sdf 200 0 sdf; else echo "==== $P: no SDF ($C), annotated run skipped"; fi
fi
if [[ $KIND == volt || $KIND == all ]]; then
  for cv in "${LOWV[@]}"; do corner=${cv%%:*}; libs=${cv#*:}
    for t in ${T0}_md0_full ${T0}_idle_full; do [[ -f $ROOT/sim/build_$t/toggles.tsv ]] || continue; echo "==== $P $C $t at $corner"; sta_run $ROOT/sim/build_$t/toggles.tsv $ROOT/power/out_vcd_${t}_$corner "$libs"; done
  done
  [[ ${#LOWV[@]} -eq 0 ]] && echo "==== $P: no other characterized supply (typical liberty only)"
fi
echo "==== $P $C $KIND done ($(date +%H:%M:%S))"
