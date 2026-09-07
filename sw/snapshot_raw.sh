#!/usr/bin/env bash
# Copy the raw reports behind every number into results/raw/ (small text files only).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; OUT="$ROOT/results/raw"; rm -rf "$OUT"; mkdir -p "$OUT"
for D in bmi_snn_top bmi_snn_topg bmi_snn_scmem bmi_snn_lmem bmi_snn_lmin bmi_snn_lmem2 bmi_snn_lmin2 bmi_snn_hw bmi_snn_min bmi_snn_ming bmi_snn_m12 bmi_snn_sp bmi_snn_min32 bmi_snn_min16; do
  R="$ROOT/synthesis/$D/runs/$D"; [ -f "$R/final/metrics.json" ] || R="$ROOT/synthesis/${D}_lo/runs/${D}_lo2"; [ -f "$R/final/metrics.json" ] || R="$ROOT/synthesis/${D}_lo/runs/${D}_lo"; [ -d "$R" ] || continue
  mkdir -p "$OUT/$D/pnr" && cp "$R/synthesis_results.txt" "$R/final/metrics.json" "$OUT/$D/pnr/" 2>/dev/null || true
  # STA path reports are 5-16 MB each: keep the worst paths only (first 400 lines)
  for c in nom_tt_025C_1v80 max_ss_100C_1v60; do mkdir -p "$OUT/$D/pnr/$c"; for k in max min; do f=$(ls "$R"/*-openroad-stapostpnr/$c/$k.rpt 2>/dev/null | head -1); [ -n "$f" ] && head -n 400 "$f" > "$OUT/$D/pnr/$c/${k}_worst.rpt"; done; done
done
for t in gls_md0_full gls_md1_full gls_idle2_full gls_md0 gls_md1 $(cd "$ROOT/sim" && ls -d build_bmi_snn_* 2>/dev/null | sed 's/^build_//'); do
  [ -d "$ROOT/sim/build_$t" ] || continue
  mkdir -p "$OUT/runs/$t" && cp "$ROOT/sim/build_$t"/{vvp.log,stats.txt} "$OUT/runs/$t/" 2>/dev/null || true
  [ -d "$ROOT/power/out_vcd_$t" ] && cp "$ROOT/power/out_vcd_$t"/*.rpt "$OUT/runs/$t/" 2>/dev/null || true
  [ -d "$ROOT/power/out_$t" ] && cp "$ROOT/power/out_$t"/*.{txt,rpt,json} "$OUT/runs/$t/" 2>/dev/null || true
done
# voltage-scaling study: the same waveforms evaluated at other corners
for d in "$ROOT"/power/out_vcd_*_sdf_*; do [ -d "$d" ] || continue; b=$(basename "$d" | sed "s/^out_vcd_//"); mkdir -p "$OUT/corners/$b"; cp "$d"/{power_vcd.rpt,slack.txt} "$OUT/corners/$b/" 2>/dev/null || true; done
mkdir -p "$OUT/riscv" && cp "$ROOT/sim/build_riscv_gls/vvp.log" "$OUT/riscv/" 2>/dev/null || true
cp "$ROOT/power/out_riscv"/*.{txt,rpt,json} "$OUT/riscv/" 2>/dev/null || true; cp "$ROOT/results/riscv_cycles.json" "$OUT/riscv/" 2>/dev/null || true
mkdir -p "$OUT/models" && for d in "$ROOT"/results/models/*_drop "$ROOT"/results/models/*_drop_p0.*; do b=$(basename "$d"); mkdir -p "$OUT/models/$b"; cp "$d"/{train.json,eval_int.json} "$OUT/models/$b/" 2>/dev/null || true; done
cp "$ROOT/results/results.json" "$ROOT/results/designs.json" "$ROOT/results/DESIGNS.md" "$ROOT/results/corners.json" "$OUT/" 2>/dev/null || true; mkdir -p "$OUT/explore" && cp "$ROOT"/results/explore/*.json "$OUT/explore/" 2>/dev/null || true
du -sh "$OUT"; find "$OUT" -type f | wc -l
