#!/usr/bin/env bash
# Round 5: full measurement pipeline of one sky130 core at 5 MHz. Waits for the policy result (runs/<design>_5m), then runs
# measure_design (500/200-bin windows of indy_20160630_01, idle run), the full test blocks (E4, zero-delay, streamed) and the
# 5,000-bin annotated windows (E4). Session policy: a hardwired core carries the weights of one session, so its full block is
# that session's (indy_20160630_01 for the main cores, the own session for the per-session netlists *_s622/*_s131); the
# programmable cores (top, topg, scmem, lmem, lmem2, lmin, lmin2) load each session's weights: full block of indy_20160630_01
# and 20,000 bins of the other two. Steps whose power report exists are skipped. Usage: pipeline5.sh <design>
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; D="$1"
export RUN_TAG="${D}_5m" CLK_NS=200
case "$D" in
  *_s622) SESS="indy_20160622_01"; NB=(full) ;;
  *_s131) SESS="indy_20170131_02"; NB=(full) ;;
  bmi_snn_top|bmi_snn_topg) SESS="indy_20160630_01 indy_20160622_01 indy_20170131_02"; NB=(full 20000 20000); NBSDF=2000 ;;              # E4: full block of B, >= 20k bins of A and C, >= 2,000 annotated
  bmi_snn_scmem|bmi_snn_lmem|bmi_snn_lmem2|bmi_snn_lmin|bmi_snn_lmin2) SESS="indy_20160630_01 indy_20160622_01 indy_20170131_02"; NB=(5000 5000 5000) ;;   # E4: >= 5,000 bins (400k-instance memories)
  *) SESS="indy_20160630_01"; NB=(full) ;;
esac
NBSDF="${NBSDF:-5000}"
NOSDF="bmi_snn_scmem bmi_snn_lmem bmi_snn_lmin bmi_snn_lmem2 bmi_snn_lmin2"   # SDF annotation of the latch/register memories does not complete in Icarus
while [[ ! -e "$ROOT/synthesis/$D/runs/${RUN_TAG}/final/metrics.json" ]]; do sleep 120; done
echo "==== pipeline5 $D start ($(date +%H:%M))"
[[ -f "$ROOT/power/out_vcd_${RUN_TAG}_md0_full/power_vcd.rpt" ]] || "$ROOT/sim/measure_design.sh" "$D" func
[[ -f "$ROOT/power/out_vcd_${RUN_TAG}_md0_sdf/power_vcd.rpt" || " $NOSDF " == *" $D "* ]] || "$ROOT/sim/measure_design.sh" "$D" sdf
i=0
for S in $SESS; do
  nb=${NB[$i]}; i=$((i+1)); tag="${RUN_TAG}_func_full_$S"; [[ "$nb" != "full" ]] && tag="${RUN_TAG}_func_w${nb}_$S"
  [[ -f "$ROOT/power/out_$tag/power_vcd.rpt" ]] || "$ROOT/sim/measure_full.sh" "$D" "$S" func "$nb"
done
if [[ " $NOSDF " != *" $D "* ]]; then
  for S in $SESS; do [[ -f "$ROOT/power/out_${RUN_TAG}_sdf_w${NBSDF}_$S/power_vcd.rpt" ]] || "$ROOT/sim/measure_full.sh" "$D" "$S" sdf $NBSDF; done
fi
echo "==== pipeline5 $D done ($(date +%H:%M))"
