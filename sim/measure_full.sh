#!/usr/bin/env bash
# Round 5 (E4): energy of one core over a long window (full test block by default) with the streamed toggle accumulation.
# Usage: RUN_TAG=<design>_5m CLK_NS=200 ./sim/measure_full.sh <design> <session> [func|sdf] [n_bins|full]
#   func: zero-delay simulation of the full test block of <session>;  sdf: annotated simulation of the first n_bins (default 5000)
# Output: sim/build_<RUN_TAG>_<kind>_full_<session>/toggles.tsv and power/out_full_<RUN_TAG>_<kind>_<session>/power_vcd.rpt
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$1"; S="$2"; KIND="${3:-func}"; NB="${4:-}"
RUN_TAG="${RUN_TAG:-$D}"; CLK_NS="${CLK_NS:-20}"; export RUN_DIR="$ROOT/synthesis/$D/runs/$RUN_TAG"
case "$D" in
  bmi_snn_top|bmi_snn_topg) LOAD="-DLOAD_BACKDOOR"; MACRO="u_wmem"; VP=""; export LIB_SRAM="$ROOT/synthesis/bmi_snn_top/macros/sram22_2048x32m8w8_tt_025C_1v80_pwr.lib" ;;   # round 5: vdd-only SRAM22 liberty as the primary figure (E11)
  bmi_snn_hw|bmi_snn_scmem) LOAD=""; MACRO="none"; VP="" ;;
  bmi_snn_min|bmi_snn_ming) LOAD=""; MACRO="none"; VP="v16_" ;;
  bmi_snn_m12)   LOAD=""; MACRO="none"; VP="v12_" ;;
  bmi_snn_sp)    LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/sp"; VP="sp_" ;;
  bmi_snn_lmem|bmi_snn_lmem2) LOAD="-DLOAD_PORT -DDUMP_AFTER_LOAD -DHAS_WR_READY"; MACRO="none"; VP="" ;;
  bmi_snn_lmin|bmi_snn_lmin2) LOAD="-DLOAD_PORT -DDUMP_AFTER_LOAD -DHAS_WR_READY"; MACRO="none"; VP="v12_" ;;
  bmi_snn_min32) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/h32"; VP="h32_" ;;
  bmi_snn_min16) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/h16"; VP="h16_" ;;
  bmi_snn_g128|bmi_snn_g128p25|bmi_snn_g128p125|bmi_snn_g64p50|bmi_snn_g64p125|bmi_snn_g32p50|bmi_snn_g32p25|bmi_snn_g16p50) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/${D#bmi_snn_}"; VP="${D#bmi_snn_}_" ;;   # E2 grid
  bmi_snn_sp_s622|bmi_snn_sp_s131)       LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/sp_${D##*_}";  VP="sp_" ;;    # E3 per-session netlists (own session vectors)
  bmi_snn_min32_s622|bmi_snn_min32_s131) LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/h32_${D##*_}"; VP="h32_" ;;
  bmi_snn_m12_s622|bmi_snn_m12_s131)     LOAD=""; MACRO="none"; export INCDIR="$ROOT/rtl/m12_${D##*_}"; VP="v12_" ;;
  *) echo "unknown design $D"; exit 2 ;;
esac
VEC="${VEC:-$ROOT/sim/vecfull_${VP}${S}}"; [[ -d "$VEC" ]] || { echo "no vectors $VEC"; exit 2; }
TOTAL=$(grep -c '^ff$' "$VEC/stream.hex")
if [[ "$KIND" == "func" ]]; then EXTRA="--no-sdf"; [[ -z "$NB" || "$NB" == "full" ]] && NB=$TOTAL; else EXTRA=""; [[ -z "$NB" || "$NB" == "full" ]] && NB=5000; fi
[[ $NB -gt $TOTAL ]] && NB=$TOTAL
TAG="${RUN_TAG}_${KIND}_full_${S}"; [[ "$NB" != "$TOTAL" ]] && TAG="${RUN_TAG}_${KIND}_w${NB}_${S}"
echo "==== $D ($RUN_TAG) $KIND $S: $NB of $TOTAL bins, clock $CLK_NS ns ($(date +%H:%M:%S))"
DESIGN=$D DUT=$D LOAD="$LOAD" DUMP_LEVEL=0 TAG=$TAG CLK_NS=$CLK_NS EXTRA_DEFS="-DTIMEOUT_CYCLES=2000000000 -DMAX_TOKENS=1400000" \
  "$ROOT/sim/run_gls_stream.sh" "$VEC" $NB 0 0 $EXTRA > "$ROOT/logs/$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/$TAG.log"; exit 1; }
grep -E "SUMMARY|PASS|FAIL|real|vcd_toggles" "$ROOT/logs/$TAG.log"
OUT="$ROOT/power/out_$TAG"
DESIGN=$D MACRO_INST=$MACRO PERIOD_NS=$CLK_NS RUN_DIR="$RUN_DIR" "$ROOT/power/run_toggles_power.sh" core "$ROOT/sim/build_$TAG/toggles.tsv" "$OUT" > "$ROOT/logs/power_$TAG.log" 2>&1 || { tail -5 "$ROOT/logs/power_$TAG.log"; exit 1; }
grep -E "annotated|^Total" "$ROOT/logs/power_$TAG.log" "$OUT/power_vcd.rpt" | head -3
echo "==== $TAG done ($(date +%H:%M:%S))"
