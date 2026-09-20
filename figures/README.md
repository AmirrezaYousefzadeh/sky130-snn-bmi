# Round-5 figures (deliverable folder)

Every figure here is regenerated from the JSON/CSV results by the script named next to it (`.venv/bin/python figures/<script>`,
or `sw/refresh_round5.sh` for all of them). Each script writes the PDF and PNG both here and to the manuscript's figure folder,
and a CSV of the plotted data next to the figure.

| figure | files | script | data |
|---|---|---|---|
| F1 energy against accuracy, every hardened sky130 core at 5 MHz | `pareto.pdf/.png`, `pareto_points.csv` | `fig_pareto.py` | `results/pareto.csv` (E2), `results/designs.json` (E1), `results/raw/designs.json` (50 MHz latch core fallback), `paper/numbers_software5.tex` (E7) |
| F2 average core power against decode rate, per kit and flavour | `pavg_vs_rate.pdf/.png`, `pavg_vs_rate.csv` | `fig_pavg_vs_rate.py` | `results/pdks5.json` (E5), `results/corners5.json` (E14), 100 C idle re-evaluation reports |
| F3 annotated power breakdown and average power at 250 bins/s | `power_breakdown5.pdf/.png`, `power_breakdown5.csv` | `fig_power_breakdown5.py` | `results/designs.json` per-pin group reports, 100 C idle re-evaluation |
| F5 accuracy bars with architecture legend | `r2.pdf/.png` | `sw/fig_accuracy.py` | `results/results.json`, NeuroBench baselines |
| F4 architecture figure (TikZ) | `paper/figures/arch-improved.tikz` (manuscript source, not copied here) | -- | -- |

Conventions: 8 pt sans-serif text, colourblind-safe (Okabe-Ito) palette, one legend per figure, no title inside the plot.
