#!/usr/bin/env python3
"""Regenerate results/BASELINE.md (sequential core vs dense vs CPU) and refresh the number sections of
README.md and competition/RULES.md from results/results.json and results/DESIGNS.md."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
R = json.load(open(ROOT / "results/results.json")); e = R["core"]["event"]; d = R["core"]["dense"]; c = R["riscv"]; p = R["core"]["pnr"]
rows = [("test R² (mean of 3 Indy sessions)", f"{R['mean_test_r2']:.3f}", "", ""),
        ("active cycles / bin", f"{e['active_cycles_per_bin_full']:.0f}", f"{d['active_cycles_per_bin_full']:.0f}", f"{c['cycles']['cycles_per_bin']:.0f}"),
        ("energy / 4 ms bin, functional activity (nJ)", f"{e['energy_per_bin_nJ_active']:.1f}", f"{d['energy_per_bin_nJ_active']:.0f}", f"{c['energy_per_bin_nJ_active']:.0f}"),
        ("decode latency (µs)", f"{e['latency_us']:.2f}", f"{d['latency_us']:.1f}", f"{c['latency_us']:.0f}"),
        ("idle power, clock running (µW)", f"{e['idle_power_uW_50MHz']:.1f}", f"{d['idle_power_uW_50MHz']:.1f}", f"{c['idle_power_uW_50MHz']:.0f}"),
        ("leakage (µW)", f"{e['leakage_uW']:.2f}", f"{d['leakage_uW']:.2f}", f"{c['leakage_uW']:.2f}"),
        ("avg power @250 bins/s, clock running (µW)", f"{e['avg_power_uW_realtime_50MHz_idle_clock']:.1f}", f"{d['avg_power_uW_realtime_50MHz_idle_clock']:.0f}", f"{c['avg_power_uW_realtime_50MHz_idle_clock']:.0f}"),
        ("avg power @250 bins/s, clock stopped (µW)", f"{e['avg_power_uW_realtime_leak_only']:.1f}", f"{d['avg_power_uW_realtime_leak_only']:.0f}", f"{c['avg_power_uW_realtime_leak_only']:.0f}"),
        ("area (mm², cells + macro)", f"{p['instance_area_um2']/1e6:.3f}", "same netlist", "1.422 (2 macros)"),
        ("clock (MHz)", "50", "50", "50")]
base = "| metric | sequential SRAM core (event) | dense mode (same netlist) | RISC-V SoC (software) |\n|---|---|---|---|\n" + "\n".join(f"| {a} | {b} | {c_} | {d_} |" for a, b, c_, d_ in rows)
(ROOT / "results/BASELINE.md").write_text("# Sequential SRAM core vs conventional references (sky130 TT 1.8 V 25 °C, 50 MHz, per-pin OpenSTA power on functional gate-level activity)\n\n" + base + "\n")
designs = (ROOT / "results/DESIGNS.md").read_text().split("\n", 2)[2].strip()
def replace_section(path, start_marker, new_body):
    s = path.read_text()
    i = s.index(start_marker); j = s.find("\n## ", i + len(start_marker)); j = len(s) if j < 0 else j
    path.write_text(s[:i] + start_marker + "\n\n" + new_body.rstrip() + "\n\n" + s[j:].lstrip("\n"))
readme_body = ("**Sequential SRAM core against the conventional references** (`results/BASELINE.md`):\n\n" + base +
               "\n\n**Weight storage and parallelism, all core variants** (`results/DESIGNS.md`; energy per bin functional and SDF, per-pin OpenSTA):\n\n" + designs +
               "\n\nSee `results/results.json`, `results/designs.json` and `results/raw/` for every field and the reports behind them.")
replace_section(ROOT / "README.md", "## Baseline numbers (this repository, sky130 TT 1.8 V 25 °C)", readme_body)
rules_body = ("Cores of this repository on sky130 (sky130_fd_sc_hd, 50 MHz; per-pin OpenSTA power; E_bin with SDF-annotated activity where\navailable):\n\n" + designs +
              "\n\nReference points on the same node: the sequential SRAM core in dense mode (all synapses visited) and the same algorithm in C\n"
              "on an open VexRiscv SoC (`results/BASELINE.md`). Two categories are ranked separately: *programmable* (weights loadable at\n"
              "run time; baseline = register-file core) and *fixed-weight* (baseline = hardwired H=32 core). The numbers to beat are the\n"
              "SDF energies per bin of those two rows at R² = 0.583 / 0.572.")
replace_section(ROOT / "competition/RULES.md", "## 6. Baseline (this repository)", rules_body)
print("BASELINE.md, README.md and RULES.md refreshed")
