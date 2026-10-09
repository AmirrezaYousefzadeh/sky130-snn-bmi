#!/usr/bin/env bash
# Round 10: assemble deliverables_round10/ (repo root, committed) and paper/deliverables_round10/ (hand-over copy, git-ignored):
# results CSVs + round10.json + consistency table, LaTeX table bodies, figures with their script, the run log with the generated
# tables appended, the grid file, the incident notes. Usage: assemble_deliverables10.sh
set -euo pipefail; cd "$(dirname "$0")/.."
.venv/bin/python sw/collect_round10.py > logs/rt10/collect_last.log 2>&1 || { tail -5 logs/rt10/collect_last.log; exit 1; }
.venv/bin/python figures/fig_power_breakdown10.py > /dev/null; .venv/bin/python figures/fig_power_breakdown10.py --statecorr > /dev/null
# run log: the static text plus the generated tables (regenerated on every assembly)
python3 - <<'PY'
import subprocess, pathlib, re
log = pathlib.Path("results/run_log_round10.md").read_text()
marker = "\n## Generated tables (sw/runlog_tables10.py, sw/collect_round10.py)\n"
log = log.split(marker)[0].rstrip("\n") + "\n"
tables = subprocess.run([".venv/bin/python", "sw/runlog_tables10.py"], capture_output=True, text=True).stdout
cons = pathlib.Path("results/consistency_round10.md").read_text()
pathlib.Path("results/run_log_round10.md").write_text(log + marker + "\n### Consistency check: round-7 sum against the real-time P_total (every existing netlist)\n\n" + cons + "\n" + tables)
PY
D=deliverables_round10; mkdir -p $D/results $D/tables $D/figures
cp -f results/table2_round10.csv results/table3_round10.csv results/grid_round10.csv results/round10.json results/consistency_round10.md results/run_log_round10.md $D/results/
cp -f figures/fig_power_breakdown10.py $D/figures/; [ -f logs/rt10/incidents.txt ] && cp -f logs/rt10/incidents.txt $D/results/incidents_round10.txt
cp -f $D/results/run_log_round10.md $D/run_log_round10.md
mkdir -p paper/deliverables_round10; rsync -a --delete $D/ paper/deliverables_round10/
echo "assembled $(date +%H:%M:%S): $(ls $D/results | wc -l) result files, $(ls $D/tables) , $(ls $D/figures | wc -l) figure files; copy in paper/deliverables_round10/"
