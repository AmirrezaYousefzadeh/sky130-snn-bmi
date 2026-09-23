#!/usr/bin/env bash
# Round 6 (E6): power of the front end + pruned core system (rtl/bmi_sys.v over the routed netlists) from the 500-bin real-time
# co-simulation: streamed toggle counts -> per-pin OpenSTA power with both blocks' SPEFs, two clocks (clk5 200 ns, clk32k 30517.578 ns,
# asynchronous; no clock-gate stop since round 6), then the round-5 root-clock correction for the clk5 root network of the
# front end (OpenSTA charges it at the full clock rate; the oscillator runs only while osc_en). Usage: measure_sys.sh [n_bins=500] [tag=sys_sp_gls_5m]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; NB="${1:-500}"; CORE="${CORE:-sp}"; TAG="${2:-sys_${CORE}_gls_5m}"
# round 7 (fix 7): CORE=lmin2 co-simulates the gated 12-bit latch core (rtl/bmi_sys_lmin2.v; weights loaded through the write port, dense 12/14-bit vectors)
FE_RUN="${FE_RUN:-$ROOT/synthesis/bmi_fe/runs/bmi_fe_5m}"; CORE_RUN="${CORE_RUN:-$ROOT/synthesis/bmi_snn_${CORE}/runs/bmi_snn_${CORE}_5m}"
FE_NL="$FE_RUN/final/nl/bmi_fe.nl.v"; CORE_NL="$CORE_RUN/final/nl/bmi_snn_${CORE}.nl.v"
if [[ $CORE == lmin2 ]]; then export SYS_RTL="$ROOT/rtl/bmi_sys_lmin2.v" VEC="$ROOT/sim/vec_v12_indy_20160630_01" EXTRA_DEFS="-DSYS_CORE_LOAD -DWEIGHTS_HEX=\"$ROOT/sim/vec_v12_indy_20160630_01/weights.hex\""; else export SYS_RTL="$ROOT/rtl/bmi_sys.v"; fi
echo "==== E6 $TAG: $NB bins ($(date +%H:%M:%S)); front end $(readlink -f $FE_RUN | xargs basename), core $(readlink -f $CORE_RUN | xargs basename)"
FE_NL="$FE_NL" CORE_NL="$CORE_NL" TAG="$TAG" "$ROOT/sim/run_sys.sh" "$NB" --stream
grep -q '^PASS' "$ROOT/sim/build_$TAG/vvp.log" || { echo "co-simulation did not pass"; exit 1; }
export DESIGN=$(basename "$SYS_RTL" .v) TOP=$(basename "$SYS_RTL" .v) RUN_DIR="$FE_RUN" MACRO_INST=none PERIOD_NS=200 VCD_SCOPE=tb_bmi_sys/u_sys CLK_PORT=clk5 CLK2_PORT=clk32k CLK2_PERIOD=30517.578 CLK_STOP_ICG=0   # round 6 finding: the clock-gate stop removes the combinational power behind the gates; OpenSTA handles the integrated clock gates itself
export NETLIST="$FE_NL $CORE_NL $SYS_RTL" SPEF="u_fe:$FE_RUN/final/spef/nom/bmi_fe.nom.spef u_core:$CORE_RUN/final/spef/nom/bmi_snn_${CORE}.nom.spef"
"$ROOT/power/run_toggles_power.sh" core "$ROOT/sim/build_$TAG/toggles.tsv" "$ROOT/power/out_vcd_$TAG" > "$ROOT/logs/power_$TAG.log" 2>&1 || { tail -8 "$ROOT/logs/power_$TAG.log"; exit 1; }
GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0 "$ROOT/power/run_toggles_power.sh" core "$ROOT/sim/build_$TAG/toggles.tsv" "$ROOT/power/out_vcd_${TAG}_noclk" > "$ROOT/logs/power_${TAG}_noclk.log" 2>&1 || { tail -8 "$ROOT/logs/power_${TAG}_noclk.log"; exit 1; }
# oscillator duty from the co-simulation summary (osc_on_cycles x 200 ns over the simulated time)
DUTY=$(python3 - "$ROOT/sim/build_$TAG/vvp.log" "$NB" <<'PY'
import re, sys
s = re.search(r"SUMMARY: .*osc_on_cycles=(\d+)", open(sys.argv[1]).read()); print(int(s.group(1)) * 200e-9 / (int(sys.argv[2]) * 131 / 32768.0))
PY
)
echo "oscillator duty $DUTY"
python3 "$ROOT/power/root_clock_correction.py" "$FE_NL" clk5 "$DUTY" "$ROOT/power/out_vcd_$TAG/power_vcd_by_instance.rpt" "$ROOT/power/out_vcd_${TAG}_noclk/power_vcd_by_instance.rpt" --prefix u_fe/ -o "$ROOT/power/out_vcd_$TAG/root_clock_correction.json" | tail -6
grep -E '^Total' "$ROOT/power/out_vcd_$TAG/power_vcd.rpt"
echo "==== E6 $TAG done ($(date +%H:%M:%S))"
