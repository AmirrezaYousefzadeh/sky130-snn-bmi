# Round 7: fixes to the round-6 deliverables (23 Sep 2026, evening)

Requested in `paper/fixes_round7_for_agent.md`. Previous versions of every replaced file: `paper/_superseded/2026-09-23_before_round7_fixes/`
(numbers*.tex, *_table*.tex, the four figures, designs.json, pdks5.json, leak_split6.*, pareto.csv, frontend.json). The manuscript files
(`main.tex`, `results.tex`, `appendix.tex`) were not touched. Regeneration: `sw/refresh_round6.sh` (collectors, tables, figures, raw snapshot,
paper build; all steps ok, paper compiles).

## 1. Memory cores: the "5,000-bin annotated" slot held the 50-bin window (fixed)
`sw/collect_designs5.py`: when a core's annotated run covers fewer bins than its zero-delay block (`full.<s>.sdf.tb.bins <
full.<s>.func.tb.bins`, the case of the latch and register-file cores whose annotated runs are the 50-bin E9 windows), the block's
annotated energy is now derived as zero-delay block energy x glitch factor (the rule of the paper's `\eSdfBlk*` preamble macros) and
flagged `derived`; the short window itself is kept as `full.<s>.sdf_short`. Values now:
| core | zero-delay block (nJ) | glitch factor (50-bin window) | derived block annotated (nJ) | 50-bin annotated window (nJ) | P_avg 250 bins/s from it (uW) |
|---|---|---|---|---|---|
| latch 12-bit gated (lmin2) | 5.72 | 1.082 | **6.18** | 4.28 (3.12 ch./bin) | 5.93 |
| register file (scmem) | 9.54 | 1.104 | **10.5** | 7.82 | -- (not in the kit table) |
Consumers corrected: `figures/fig_pareto.py` (`block_ann` + new `block_kind`: the latch point sits at 6.18 nJ, its legend kind reads
"zero-delay block x glitch factor 1.08 (50-bin annotated window)"), `figures/fig_power_breakdown5.py` (latch bar 6.2 with the derived
dagger, P_avg 5.9), `sw/collect_pdks5.py` (sky130 LmMinP row of `pdks_table.tex`: "E ann. 5k" = 6.18 with a double-dagger footnote,
P_avg 5.93; the hand-edited row of the paper folder is thereby reproduced by the generator). New macros in `numbers2.tex`:
`\eSdfShort<Core><Session>`, `\nbSdfShort*`, `\evSdfShort*` (the 50-bin window under its own name); `\eSdfW<Core><Session>` is the block
value (derived for the memory cores) and `\nbSdfW*` the bins it refers to. `\eSdfWLmMinPB` = 6.18 equals the paper's `\eSdfBlkLmMinP`.

## 2. F3 `power_breakdown5`: clipped y labels, "6" label (fixed)
Labels shortened to "decode-time power share (%)" and "$P_\mathrm{avg}$ at 250 bins/s (µW)", figure height 3.0 -> 3.3 in; the energy
labels above the bars use two significant digits with a trailing zero ("6.0", "9.0"). Checked in the PNG: both labels complete.

## 3. F2 `pavg_vs_rate`: duplicate legend entry (fixed)
The "sky130, 1.8 V, leakage at 37 C" legend line was added for every kit that had a dotted curve (IHP's logic-only line is dotted);
now only for sky130. Legend: 11 entries, none repeated.

## 4. Convention of `\pdkpavgLogic*` and `\pdkpavgNoDecap*` (fixed)
Both are now built from the same window as `\pdkpavgSdfW*` (5,000-bin annotated; else the 200-bin annotated; else zero-delay), and the
zero-delay versions are kept as `\pdkpavgLogicFunc*` and `\pdkpavgNoDecapFunc*`; `pdks5.json` records the window used (`pavg_window`).
Example: `\pdkpavgLogicSkySp` 0.749 -> 0.781 uW, `\pdkpavgNoDecapIhpSp` 4.30 (unchanged: IHP's decode energy is small next to its leakage).

## 5. Trailing zeros (fixed)
`sw/fmt3.py`: one formatter for every generated macro and table cell - three significant digits with trailing zeros (3.00, 5.70, 1.10,
0.0720, 0.700, 0.580), integers and values >= 1,000 as integers with thousands separators; used by all collectors (`collect_designs5`
through `collect_designs._f`, `collect_pdks5`, `collect_pareto`, `collect_persession`, `collect_corners5`, `collect_frontend`,
`collect_software5/6`, `collect_transfer5`, `collect_util_sweep6`, `collect_results._fmt`). The values named in the request now read
`\eWFiveHSdfSp` 3.00, `\eWHundSdfMinT` 5.70, `\sdfRatioRf` 1.10, `\sweepAsapSSeventye` 0.0720, `\fePower` 0.700, `\rsqGridGeDense` 0.580.
Side effect to know: values that are exactly integers print without decimals (utilizations, counts, "5 V"), 1.8 V prints as "1.80" where
a macro is asked for two digits (`\pdkvolt*` with nd=2 -> "1.8" is preserved because 1.8 has two significant digits already).

## 6. IHP 32-neuron 50 % core: leakage split (done)
`sw/leak_split6.py` rerun on `power/out_vcd_pdk5_ihp_g32p50_idle_full`: fill 0, decap 33.3, tap 0, diode 0.00469 uW of
35.6 uW total (94 % decap, as for the pruned core on this kit); macros `\pdkleak<Fill|Decap|Tap|Diode>IhpGcHalf` filled,
`results/leak_split6.{csv,json}` updated.

## 7. Optional: front end + gated 12-bit latch core co-simulated (done)
`rtl/bmi_sys_lmin2.v` (the wrapper of E6 with `bmi_snn_lmin2` as the core, its weight-write port exposed and a separate core reset),
`sim/tb_bmi_sys.v` (`-DSYS_CORE_LOAD`: the testbench loads the 1,664 weight words through the write port with the `wr_ready` handshake
while the front end is still in reset - the front end opens the core clock gate during reset, so the core clock runs -, then starts the
dump and releases the front end), `sim/run_sys.sh` (`SYS_RTL`), `sim/measure_sys.sh` (`CORE=lmin2`: netlist, SPEF, dense 12/14-bit vectors
of indy_20160630_01; the clock-gate stop that the script still carried from round 5 is off now). 500 bins in real time, 2,934 events,
every channel serialized once, 500 ticks, every output bit-exact; the weight load took 2,083 core clock cycles and is outside the
power window. Per-pin power on both routed netlists (two SPEFs, two clocks), root-clock correction of the front end's `clk5` network:
| | front end (corrected) | core | of which leakage | core dynamic | core energy per bin (in system, zero-delay) | **system** |
|---|---|---|---|---|---|---|
| latch core (lmin2) | 0.649 uW | 5.56 uW | 4.38 uW | 1.18 uW | 4.70 nJ | **6.21 uW** |
| pruned core (round 6, for comparison) | 0.644 uW | 0.865 uW | 0.244 uW | 0.621 uW | 2.48 nJ | 1.51 uW |
The core alone (round-5/6 measurements at 250 bins/s): zero-delay 500-bin window 6.21 nJ -> 5.94 uW; the paper's sum
(front end 0.700 + 6.18 nJ x 250/s + 4.38 uW leakage) = 6.63 uW. The measured system draws 6.21 uW, 6.4 % below the
sum (6.5 % below the zero-delay sum), the same burst effect as for the pruned core: inside the system the core spends
4.70 nJ per bin against 6.21 alone (the front end delivers each bin's events back to back; 22.3 core clock cycles
per bin). The system is leakage-dominated (71 % of it is the latch core's leakage at the 20 % floorplan). Macros in
`numbers_frontend.tex`: `\pSysLmMinP`, `\pSysFeLmMinP`, `\pSysCoreLmMinP`, `\pSysCoreDynLmMinP`, `\eSysCoreLmMinP`, `\pSysCoreAloneLmMinP`,
`\eSysCoreAloneLmMinP`, `\pSysSumSeparateLmMinP` (zero-delay sum), `\pSysSumSeparateAnnLmMinP` (the paper's annotated sum),
`\pSysVsSumPctLmMinP`, `\pSysVsSumAnnPctLmMinP`, `\sysCoreClkPerBinLmMinP`; the pruned-core names of round 6 are unchanged and gained
`\pSysSumSeparateAnnSp` and `\pSysVsSumAnnPctSp`.
**Action for the manuscript:** `main.tex` line 90 defines `\pSysLmMinP` itself (`\fpeval{round(\fePower+\eSdfBlkLmMinP*0.25+\leakLmMinP,1)}`);
with the generated macro that line must go (LaTeX: "Command \pSysLmMinP already defined"). The paper compiles with it removed (checked on a
scratch copy) and fails with it present. Section 6.2's "sum of the two blocks (6.6 uW)" can become the measurement (6.2 uW).

## Hand back
`paper/deliverables_round7/`: this log, the regenerated `numbers*.tex` and tables (12 changed files, listed in `CHANGED_FILES.txt`),
F1-F4 as PDF and PNG with their scripts, `leak_split6.csv/json`, `results/designs.json`, `results/pdks5.json`, `results/frontend.json`,
and `_superseded/2026-09-23_before_round7_fixes/` with every replaced file. Repository commit follows.
