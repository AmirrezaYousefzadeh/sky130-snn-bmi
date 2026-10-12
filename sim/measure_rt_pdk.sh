#!/usr/bin/env bash
# Round 10 (E7): real-time power measurement (sim/tb_bmi_snn.v -DREALTIME, see sim/measure_rt.sh) of a core hardened on another kit,
# on the existing round-5/6 netlists. Usage: sim/measure_rt_pdk.sh <gf180|ihp|nangate45|asap7|asap7sram> <sp|m12|min32|min16|lmin2|g32p50> [n_bins=5000] [sta]
#   default: annotated real-time run of the first n_bins (NanGate45: zero-delay, no timed models) + OpenSTA at the typical liberty,
#            the zero-data run and the root-clock correction; GF180 in addition re-evaluated with the 1.8 V and 3.3 V liberties
#   sta    : OpenSTA only on the existing toggle file (e.g. for another supply or the decap-free refill: RUN_NICK=<nick> TAG_SFX=_nodecap)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; P="$1"; C="$2"; NB="${3:-5000}"; KIND="${4:-run}"; D=bmi_snn_$C; ORFS=/media/pdk/OpenROAD-flow-scripts/flow; PDK=/media/pdk
RN="${RUN_NICK:-${D}_5m}"; TS="${TAG_SFX:-}"
case $C in
  sp)    VP=sp_;  INC=$ROOT/rtl/sp;  LOAD="" ;;
  m12)   VP=v12_; INC=$ROOT/rtl;     LOAD="" ;;
  min32) VP=h32_; INC=$ROOT/rtl/h32; LOAD="" ;;
  min16) VP=h16_; INC=$ROOT/rtl/h16; LOAD="" ;;
  lmin2) VP=v12_; INC=$ROOT/rtl;     LOAD="-DLOAD_PORT -DHAS_WR_READY" ;;
  g32p50) VP=g32p50_; INC=$ROOT/rtl/g32p50; LOAD="" ;;
  *) echo "unknown core $C"; exit 2 ;;
esac
TU=1e-9; PERIOD_LIB=200; SDF_SRC=""; LOWV=(); VLOG_SDF=""; SDF_FUNC=""; CLKP=clk
case $P in
  gf180) RUN=$ROOT/synthesis/pdk_gf180/$D/runs/$RN; NL=$RUN/final/nl/$D.nl.v; SPEF=$RUN/final/spef/nom/$D.nom.spef
         LIBDIR=$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/lib; LIB="$LIBDIR/gf180mcu_fd_sc_mcu7t5v0__tt_025C_5v00.lib"
         VLOG="$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v $PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/gf180mcu_fd_sc_mcu7t5v0.v"
         SDF_SRC="$(find $RUN/final/sdf/nom_tt_025C_5v00 -name '*.sdf' 2>/dev/null | head -1)"
         VLOG_SDF="$PDK/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0/verilog/primitives.v /media/pdk/icarus_sdf_models/gf180mcu_fd_sc_mcu7t5v0_sdf.v"; SDF_FUNC=""
         LOWV=("tt_025C_3v30:$LIBDIR/gf180mcu_fd_sc_mcu7t5v0__tt_025C_3v30.lib" "tt_025C_1v80:$LIBDIR/gf180mcu_fd_sc_mcu7t5v0__tt_025C_1v80.lib") ;;
  nangate45) RUN=$ORFS/results/nangate45/$RN/base; NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$ORFS/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib"; VLOG="/media/pdk/nangate45_models.v" ;;
  ihp)   RUN=$ORFS/results/ihp-sg13g2/$RN/base; NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$ORFS/platforms/ihp-sg13g2/lib/sg13g2_stdcell_typ_1p20V_25C.lib"; VLOG="/media/pdk/ihp_sg13g2_models_functional.v"
         VLOG_SDF="/media/pdk/IHP-Open-PDK/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_udp.v /media/pdk/icarus_sdf_models/sg13g2_stdcell_seqstripped.v $ROOT/sim/ihp_seq_icarus.v" ;;
  asap7|asap7sram) TU=1e-12; PERIOD_LIB=200000
         if [[ $P == asap7 ]]; then FL=RVT; RUN=$ORFS/results/asap7/$RN/base; else FL=SRAM; RUN=$ORFS/results/asap7/${RUN_NICK:-${D}_5m_sram}/base; fi
         NL=$RUN/6_final.v; SPEF=$RUN/6_final.spef
         LIB="$(ls $ORFS/platforms/asap7/lib/NLDM/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_${FL}_TT_nldm_*.lib* | tr '\n' ' ')"
         VLOG="$(ls /media/pdk/asap7sc7p5t_28/Verilog/asap7sc7p5t_{AO,INVBUF,OA,SEQ,SIMPLE}_${FL}_TT_*.v | tr '\n' ' ')"
         VLOG_SDF="$(ls /media/pdk/asap7sc7p5t_28/Verilog/asap7sc7p5t_{AO,INVBUF,OA,SIMPLE}_${FL}_TT_*.v | tr '\n' ' ') $ROOT/sim/asap7_seq_icarus.v" ;;
  *) echo "unknown kit $P"; exit 2 ;;
esac
[[ -f "$NL" ]] || { echo "no netlist $NL"; exit 1; }; [[ -f "$SPEF" ]] || echo "WARNING: no SPEF $SPEF"
VEC=$ROOT/sim/vecfull_${VP}indy_20160630_01; [[ -d $VEC ]] || { echo "no vectors $VEC"; exit 1; }
STUBS=$ROOT/sim/build_pdk5_${P}_${C}_stubs.v; [[ -f $STUBS ]] || $ROOT/.venv/bin/python $ROOT/sim/gen_phys_stubs.py "$NL" "$STUBS" $VLOG; VLOG="$VLOG $STUBS"
export CLK_STOP_ICG=0 UNANNOTATED_ZERO=1
MODEL=sdf; [[ $P == nangate45 ]] && MODEL=func
T0TAG=rt_pdk_${P}_${C}${TS}_${MODEL}_w${NB}; BUILD=$ROOT/sim/build_rt_pdk_${P}_${C}_${MODEL}_w${NB}
sta_all() { # <toggles.tsv> <out_dir> <liberty list> <label>: annotated run, zero-data run, root-clock correction
  local tsv=$1 out=$2 libs=$3
  DESIGN=$D MACRO_INST=none PERIOD_NS=$PERIOD_LIB LIB_TIME_UNIT_S=$TU RUN_DIR=$RUN LIB_SC="$libs" LIB_SRAM=/nonexistent NETLIST=$NL SPEF=$SPEF \
    $ROOT/power/run_toggles_power.sh core "$tsv" "$out" > "$out.log" 2>&1 || { tail -5 "$out.log"; return 1; }
  GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 DESIGN=$D MACRO_INST=none PERIOD_NS=$PERIOD_LIB LIB_TIME_UNIT_S=$TU RUN_DIR=$RUN LIB_SC="$libs" LIB_SRAM=/nonexistent NETLIST=$NL SPEF=$SPEF \
    $ROOT/power/run_toggles_power.sh core "$tsv" "${out}_zero" > "${out}_zero.log" 2>&1 || { tail -5 "${out}_zero.log"; return 1; }
  local duty; duty=$(python3 - "$(dirname $tsv)/vvp.log" <<'PY'
import re, sys
s = open(sys.argv[1]).read(); m = re.search(r"RT: bins=(\d+) clk_cycles_in_window=(\d+) .* window_ns=(\d+)", s); print(int(m.group(2)) * 200.0 / int(m.group(3)))
PY
)
  python3 $ROOT/power/root_clock_correction.py "$NL" $CLKP "$duty" "$out/power_vcd_by_instance.rpt" "${out}_zero/power_vcd_by_instance.rpt" -o "$out/root_clock_correction.json" | tail -2
  $ROOT/.venv/bin/python $ROOT/sw/annot_coverage.py "$NL" "$out" | tail -1
  grep -E "^Total" "$out/power_vcd.rpt"
  if [[ -f "$(dirname $tsv)/toggles_gated.tsv" ]]; then     # round 10: duties conditioned on the clock enable (state-dependent internal power tables of the kit)
    GATED_TSV="$(dirname $tsv)/toggles_gated.tsv" DESIGN=$D MACRO_INST=none PERIOD_NS=$PERIOD_LIB LIB_TIME_UNIT_S=$TU RUN_DIR=$RUN LIB_SC="$libs" LIB_SRAM=/nonexistent NETLIST=$NL SPEF=$SPEF \
      $ROOT/power/run_toggles_power.sh core "$tsv" "${out}_cond" > "${out}_cond.log" 2>&1 || { tail -5 "${out}_cond.log"; return 1; }
    python3 $ROOT/power/root_clock_correction.py "$NL" $CLKP "$duty" "${out}_cond/power_vcd_by_instance.rpt" "${out}_zero/power_vcd_by_instance.rpt" -o "${out}_cond/root_clock_correction.json" | tail -1
    echo "cond-duty $(grep -E '^Total' "${out}_cond/power_vcd.rpt")"
  fi
}
if [[ $KIND == run ]]; then
  echo "==== RT kit $P $C: $NB bins at 4 ms, $MODEL ($(date +%H:%M:%S))"; T0=$(date +%s)
  local_models="$VLOG"; sf=""; extra="--no-sdf"
  if [[ $MODEL == sdf ]]; then
    if [[ $P == asap7 || $P == asap7sram || $P == ihp ]]; then
      SDF_SRC=$ROOT/sim/build_pdk5_${P}_${C}_sdf_src/design.sdf; mkdir -p "$(dirname $SDF_SRC)"
      [[ -f "$SDF_SRC" ]] || DESIGN=$D RUN_DIR=$RUN LIB_SC="$LIB" NETLIST=$NL SPEF=$SPEF PERIOD_NS=$PERIOD_LIB SDF_OUT=$SDF_SRC $ROOT/power/run_write_sdf.sh > "$(dirname $SDF_SRC)/write_sdf.log" 2>&1 || tail -3 "$(dirname $SDF_SRC)/write_sdf.log"
    fi
    [[ -f "$SDF_SRC" ]] || { echo "no SDF for $P $C"; exit 1; }
    [[ -n "$VLOG_SDF" ]] && local_models="$VLOG_SDF $STUBS"; sf="$SDF_FUNC"; extra=""
  fi
  export TOGGLE_GATE="${TOGGLE_GATE-tb_bmi_snn/u_dut/core_clk_en}"
  PDK_VERILOG="$local_models" SDF_FUNCTIONAL="$sf" INCDIR=$INC DESIGN=$D DUT=$D LOAD="$LOAD" NETLIST=$NL RUN_DIR=$RUN SDF_SRC="$SDF_SRC" TAG=$(basename $BUILD | sed 's/^build_//') DUMP_LEVEL=0 CLK_NS=200 \
    EXTRA_DEFS="-DREALTIME -DTIMEOUT_CYCLES=2000000000 -DMAX_TOKENS=1400000" timeout ${SIM_TIMEOUT:-40h} $ROOT/sim/run_gls_stream.sh $VEC $NB 0 0 $extra > $ROOT/logs/$(basename $BUILD | sed 's/^build_//').log 2>&1 || { tail -5 $ROOT/logs/$(basename $BUILD | sed 's/^build_//').log; exit 1; }
  grep -E "SUMMARY|PASS|FAIL|RT:|real|SDF:" $ROOT/logs/$(basename $BUILD | sed 's/^build_//').log
  echo "SIM_WALLCLOCK_S $(( $(date +%s) - T0 ))" >> $BUILD/vvp.log
  grep -q "^PASS" $BUILD/vvp.log || { echo "simulation did not pass"; exit 1; }
fi
[[ -f $BUILD/toggles.tsv ]] || { echo "no toggle file $BUILD/toggles.tsv"; exit 1; }
echo "==== OpenSTA $P $C${TS} (typical liberty)"; sta_all $BUILD/toggles.tsv $ROOT/power/out_${T0TAG} "$LIB"
for cv in "${LOWV[@]}"; do corner=${cv%%:*}; libs=${cv#*:}; echo "==== OpenSTA $P $C${TS} at $corner"; sta_all $BUILD/toggles.tsv $ROOT/power/out_${T0TAG}_$corner "$libs"; done
echo "==== RT kit $P $C${TS} done ($(date +%H:%M:%S))"
