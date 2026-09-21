#!/usr/bin/env bash
# Round 5: rerun every collector and figure script in order (numbers*.tex, tables, CSV/JSON, figures), then the raw snapshot.
set -uo pipefail; cd "$(dirname "$0")/.."; PY=.venv/bin/python
$PY sw/collect_designs5.py > logs/refresh_designs5.log 2>&1 && echo "designs5 ok" || echo "designs5 FAILED"
$PY sw/collect_pdks5.py > logs/refresh_pdks5.log 2>&1 && echo "pdks5 ok" || echo "pdks5 FAILED"
$PY sw/collect_seeds.py > logs/refresh_seeds.log 2>&1 && echo "seeds ok" || echo "seeds FAILED"
$PY sw/collect_pareto.py > logs/refresh_pareto.log 2>&1 && echo "pareto ok" || echo "pareto FAILED"
$PY sw/collect_persession.py > logs/refresh_persession.log 2>&1 && echo "persession ok" || echo "persession FAILED"
$PY sw/collect_software5.py > logs/refresh_software5.log 2>&1 && echo "software5 ok" || echo "software5 FAILED"
$PY sw/collect_frontend.py > logs/refresh_frontend.log 2>&1 && echo "frontend ok" || echo "frontend FAILED"
$PY sw/collect_corners5.py > logs/refresh_corners5.log 2>&1 && echo "corners5 ok" || echo "corners5 FAILED"
$PY sw/collect_transfer5.py > logs/refresh_transfer5.log 2>&1 && echo "transfer5 ok" || echo "transfer5 FAILED"
$PY sw/policy_summary5.py > logs/refresh_policy5.log 2>&1 && echo "policy summary ok" || echo "policy summary FAILED"
$PY sw/closing_round5.py > logs/refresh_closing5.log 2>&1 && echo "closing tables ok" || echo "closing tables FAILED"
$PY sw/fig_accuracy.py > logs/refresh_fig_accuracy.log 2>&1 && echo "fig accuracy ok" || echo "fig accuracy FAILED"
for s in figures/fig_pareto.py figures/fig_pavg_vs_rate.py figures/fig_power_breakdown5.py; do $PY $s > logs/refresh_$(basename $s .py).log 2>&1 && echo "$s ok" || echo "$s FAILED (see logs)"; done
./sw/snapshot_raw5.sh > logs/refresh_snapshot5.log 2>&1 && echo "snapshot ok"
(cd paper && ../tools/tectonic -X compile main.tex > ../logs/refresh_tectonic.log 2>&1 && echo "paper compiles" || { echo "paper build FAILED"; grep -i error ../logs/refresh_tectonic.log | head -n 3; })
