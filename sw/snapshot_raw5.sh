#!/usr/bin/env bash
# Round 5: copy the raw reports behind the round-5 numbers into results/raw/round5/ (small text files only).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; OUT="$ROOT/results/raw/round5"; rm -rf "$OUT"; mkdir -p "$OUT"
# sky130 hardenings at 5 MHz (policy runs): accepted run, rejected attempts (metrics only), watchdog notes
for cfg in "$ROOT"/synthesis/*/config_5mhz_used.yaml "$ROOT"/synthesis/pdk_gf180/*/config_5mhz_used.yaml; do
  [ -f "$cfg" ] || continue; des=$(dirname "$cfg"); D=$(basename "$des"); pfx=""; [[ "$des" == *pdk_gf180* ]] && pfx="gf180_"
  R="$des/runs/${D}_5m"; mkdir -p "$OUT/pnr/$pfx$D"; cp "$cfg" "$OUT/pnr/$pfx$D/"; cp "$R/synthesis_results.txt" "$R/final/metrics.json" "$OUT/pnr/$pfx$D/" 2>/dev/null
  cp "$des/config_lowv.yaml" "$OUT/pnr/$pfx$D/" 2>/dev/null; RL="$des/runs/${D}_5m_lv"; [ -d "$RL" ] && { mkdir -p "$OUT/pnr/$pfx$D/lowv"; cp "$RL/synthesis_results.txt" "$RL/final/metrics.json" "$OUT/pnr/$pfx$D/lowv/" 2>/dev/null; }
  for r in "$des"/runs/${D}_5m_u*; do [ -d "$r" ] || continue; t=$(basename "$r"); mkdir -p "$OUT/pnr/$pfx$D/attempts/$t"; cp "$r/final/metrics.json" "$r/synthesis_results.txt" "$r/WATCHDOG_KILLED" "$r/KILLED_HOPELESS" "$OUT/pnr/$pfx$D/attempts/$t/" 2>/dev/null; done
done
cp "$ROOT/logs/policy_round5.log" "$ROOT/logs/orfs5_policy.log" "$OUT/" 2>/dev/null
# simulations and per-pin power of round 5 (5 MHz windows, full blocks, cross-kit runs, low-voltage, front end, SoC windows)
for b in "$ROOT"/sim/build_*_5m_* "$ROOT"/sim/build_pdk5_* "$ROOT"/sim/build_fe_gls; do
  [ -d "$b" ] || continue; t=$(basename "$b" | sed 's/^build_//'); mkdir -p "$OUT/runs/$t"
  cp "$b"/{vvp.log,stats.txt,toggles.log} "$OUT/runs/$t/" 2>/dev/null
  for d in "$ROOT/power/out_vcd_$t" "$ROOT/power/out_$t" "$ROOT"/power/out_vcd_${t}_*; do [ -d "$d" ] || continue; sub=$(basename "$d" | sed "s/^out_vcd_//; s/^out_//"); mkdir -p "$OUT/runs/$t/$sub"; cp "$d"/{power_vcd.rpt,power_vcd_clock_tree.rpt,slack.txt,activity_summary.json,root_clock_correction.json} "$OUT/runs/$t/$sub/" 2>/dev/null; grep -E "WORST|annotated|CLK_STOP|GLOBAL" "$d/sta.log" > "$OUT/runs/$t/$sub/sta_summary.txt" 2>/dev/null; done
done
for d in "$ROOT"/power/out_soc_*; do [ -d "$d" ] || continue; t=$(basename "$d"); mkdir -p "$OUT/soc/$t"; cp "$d"/window.json "$OUT/soc/$t/" 2>/dev/null; for s in pwr asgen idle/pwr; do [ -d "$d/$s" ] && { mkdir -p "$OUT/soc/$t/$s"; cp "$d/$s"/{power_vcd.rpt,activity_summary.json} "$OUT/soc/$t/$s/" 2>/dev/null; }; done; done
cp "$ROOT"/power/out_vcd_fe_*/power_vcd.rpt "$OUT/runs/" 2>/dev/null
# ORFS kits: reports of the accepted runs
ORFS="${ORFS:-/media/pdk/OpenROAD-flow-scripts/flow}"
for link in "$ORFS"/results/*/bmi_snn_*_5m "$ORFS"/results/*/bmi_snn_*_5m_sram; do [ -L "$link" ] || continue; plat=$(basename "$(dirname "$link")"); nick=$(readlink "$link"); mkdir -p "$OUT/orfs/$plat/$nick"; cp "$ORFS/logs/$plat/$nick/base/6_report.json" "$ORFS/logs/$plat/$nick/base/5_2_route.json" "$ORFS/reports/$plat/$nick/base/6_finish.rpt" "$OUT/orfs/$plat/$nick/" 2>/dev/null; cp "$ORFS/designs/$plat/${nick%_u*}/config.mk" "$ORFS/designs/$plat/${nick%_u*}/constraint.sdc" "$OUT/orfs/$plat/$nick/" 2>/dev/null; done
# models of the training grid and the collected tables
mkdir -p "$OUT/models" && for d in "$ROOT"/results/models/*_H{128,32,16,64}_th256_k44_drop*; do b=$(basename "$d"); mkdir -p "$OUT/models/$b"; cp "$d"/{train.json,eval_int.json} "$OUT/models/$b/" 2>/dev/null; done
cp "$ROOT"/results/{designs.json,DESIGNS.md,DESIGNS_50_vs_5.md,pdks5.json,pareto.csv,per_session.csv,pdks_pavg_vs_rate.csv,frontend.json,seeds.json,run_log_round5.md} "$ROOT"/results/explore/{software5.json,bootstrap.json} "$OUT/" 2>/dev/null
du -sh "$OUT"; find "$OUT" -type f | wc -l
