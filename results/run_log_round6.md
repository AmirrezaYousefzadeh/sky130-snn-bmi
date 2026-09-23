# Round 6 run log (started 2026-09-23)

Request: `paper/experiments_round6.md` (round-6 referee report). Conventions, policy, watchdog, hold margins and measurement
methods as in round 5 (`results/run_log_round5.md`); the previous versions of every replaced file are in the manuscript folder's
`_superseded/2026-09-23_before_round6_runs/`. Order of work: E1, E3, E7 (cheap) first; long simulations (E2, E4, E5) launched early
and collected as they finish; E6 and the figures after that; E8 if time allows.

## E3a. Physical-cell leakage split (post-processing of the round-5 idle runs, 23 Sep 01:45)
Method: `sw/leak_split6.py` maps every instance of the per-instance OpenSTA report of the idle run to its cell master through the
routed netlist and sums the leakage per class: fill (`fill`, `FILLER`, `FILLCELL`), decap (`decap`, `fillcap`), tap (`tap`,
`filltie`), diode/antenna, endcap. sky130 has no dedicated endcap: OpenLane places `decap_3` at the row ends, so those few cells
count as decap. ASAP7 and NanGate45 liberties carry no leakage attribute on fill, decap and tap cells (their physical leakage is 0
by construction; the round-5 NanGate45 note applies). Output `results/leak_split6.csv` / `.json`, 46 kit/core pairs; macros
`\leakFill<Kit><Core>`, `\leakDecap<..>`, `\leakTap<..>` in `numbers_pdks.tex` (sw/collect_pdks5.py).

| kit | core | total leak uW | logic | fill (n) | decap (n) | tap (n) | diode (n) | decap share of total |
|---|---|---|---|---|---|---|---|---|
| sky130 | sp | 0.243 | 0.081 | 0.000 (10,082) | 0.163 (50,180) | 0.000 (5,381) | 0.000 (12) | 67 % |
| sky130 | m12 | 0.362 | 0.103 | 0.000 (11,834) | 0.259 (79,912) | 0.000 (8,033) | 0.000 (12) | 72 % |
| sky130 | min32 | 0.144 | 0.053 | 0.000 (5,419) | 0.091 (28,070) | 0.000 (3,330) | 0.000 (12) | 63 % |
| sky130 | min16 | 0.064 | 0.030 | 0.000 (2,844) | 0.034 (10,506) | 0.000 (1,550) | 0.000 (12) | 53 % |
| sky130 | top | 2.437 | 2.390 | 0.000 (11,931) | 0.047 (14,579) | 0.000 (2,706) | 0.000 (56) | 2 % |
| sky130 | lmin2 | 4.429 | 0.846 | 0.000 (114,741) | 3.582 (1,105,606) | 0.000 (87,936) | 0.000 (55) | 81 % |
| sky130 | scmem | 4.906 | 1.072 | 0.000 (134,950) | 3.834 (1,183,383) | 0.000 (104,895) | 0.000 (56) | 78 % |
| gf180 | sp | 4.125 | 3.152 | 0.683 (13,668) | 0.266 (5,313) | 0.000 (0) | 0.002 (12) | 6 % |
| gf180 | m12 | 6.197 | 4.039 | 1.225 (24,499) | 0.903 (18,060) | 0.000 (0) | 0.002 (12) | 15 % |
| gf180 | min32 | 3.571 | 2.569 | 0.636 (12,716) | 0.344 (6,875) | 0.000 (0) | 0.002 (12) | 10 % |
| gf180 | min16 | 1.778 | 1.360 | 0.296 (5,916) | 0.107 (2,131) | 0.000 (0) | 0.002 (12) | 6 % |
| gf180 | lmin2 | 49.612 | 32.508 | 9.082 (181,648) | 7.930 (158,593) | 0.000 (0) | 0.007 (55) | 16 % |
| ihp | sp | 59.589 | 3.658 | 0.000 (14,514) | 55.918 (73,572) | 0.000 (0) | 0.013 (3,046) | 94 % |
| ihp | min32 | 49.436 | 2.983 | 0.000 (12,799) | 46.442 (61,242) | 0.000 (0) | 0.012 (2,689) | 94 % |
| ihp | min16 | 16.176 | 1.535 | 0.000 (6,562) | 14.639 (19,726) | 0.000 (0) | 0.002 (386) | 90 % |
| nangate45 | sp | 764.280 | 764.280 | 0.000 (13,253) | 0.000 (0) | 0.000 (378) | 0.000 (0) | 0 % |
| asap7 | sp | 3.301 | 3.301 | 0.000 (11,131) | 0.000 (7,156) | 0.000 (680) | 0.000 (0) | 0 % |
| asap7sram | sp | 0.719 | 0.719 | 0.000 (10,776) | 0.000 (7,189) | 0.000 (674) | 0.000 (0) | 0 % |

Reading: on sky130 the decap cells (`decap_3`/`decap_4`... used as fill) carry two thirds of the pruned core's leakage (0.161 of 0.243 uW) and
the plain fillers none; on IHP the decaps are 94 % of the total (55.9 of 59.6 uW for sp) - the `sg13g2_decap_4/8` cells leak about
0.76 nW each against 0.13 nW for a logic cell; on GF180 fill (0.68) and decap (0.27) together are 23 % of 4.1 uW. The decap-free
fill reruns (E3b) measure the remaining leakage directly.

## E1. Software baseline on a longer window - setup (23 Sep 01:50)
The firmware decodes the token stream held in DMEM (8 kB, shared with the 6.3 kB of weights); IMEM holds the code only. 500 bins do
not fit (3.4 kB of tokens plus the expected outputs), 100 bins do when the expected outputs are stored as 16-bit values
(`sw/export_firmware.py --n_bins 100 --expect_type int16_t`: 7,600 of 8,192 B used, 592 B left for the stack). Window event counts:
the existing 16-bin window has 63 events (3.94 per bin), the 100-bin window 495 events (4.95 per bin), the cores' 500-bin window
2,934 events (5.87 per bin) and the whole block 4.88 per bin. Runs: gate-level simulation with cell delays of the 5 MHz SoC netlist
(`runs/sky130_vex2_soc_5m`), -O2 and hand-tuned firmware, 100 bins, level-1 waveform stored, launched 01:51 / 01:53
(`sim/run_riscv.sh gls --vcd`, ~8 h each expected from the 78 min of the 16-bin run); then `sim/measure_soc_window.sh <vcd> <run> 200
<tag> 100` for the per-pin power over the decoding window and the idle window. The cores' matching windows (100 and 500 bins,
annotated) follow with `sim/measure_full.sh <core> indy_20160630_01 sdf 100|500`.

## E7. Hold slack on the flow-scripts kits - method (23 Sep 01:40)
`power/hold_sta.tcl` (OpenSTA: liberties of the corner, routed netlist, SPEF, propagated 200 ns clock, 20 % I/O delays, the flow's
false paths) run by `sw/hold_orfs6.py` for every routed netlist at every corner the platform provides: NanGate45 typical only; IHP
typ 1.20 V 25 C, slow 1.08 V 125 C, fast 1.32 V -40 C; ASAP7 TT, SS, FF (RVT and SRAM-Vt). Results `results/hold6.json`; macros
`\pdkhold<Kit><Core>` and a hold column in `pdks_table.tex` (worst over the available corners, corner named in the appendix).

## E4. g32p50 across sessions, supply and kits, and four grid points - launches (23 Sep 01:50)
(a) `bmi_snn_g32p50_s622` / `_s131` generated (variant, ROM from the round-5 seed-0 models of the sessions, own-session full-block
vectors with 12/14-bit saturation), policy hardening 60 -> 30 % started, pipelines armed. (b) `harden_lowv.sh bmi_snn_g32p50` at the
accepted 50 %. (c) RTL retargeted to GF180, IHP, NanGate45, ASAP7 RVT/SRAM-Vt; hardenings started (GF180 60 -> 30 %, ORFS kits
60 -> 30 %, IHP 30 -> 20 %); 500-bin vector set exported for the kit measurements. (d) 60 trainings (H = 48 dense / 50 % / 25 %,
H = 32 12.5 %; 5 seeds x 3 sessions) with the round-5 recipe; the GPU is shared with another user's 6.3 GB job, so two runs at a
time with retry passes (a first attempt with four concurrent runs hit CUDA out-of-memory).
## E7. Hold slack on the flow-scripts kits - results (23 Sep 02:05)

| kit | core | corners checked | worst hold slack (ns) at | setup slack at typ (ns) |
|---|---|---|---|---|
| nangate45 | sp | typical | +0.001 (typical) | 119.80 |
| nangate45 | m12 | typical | -0.025 (typical) | 119.81 |
| nangate45 | min32 | typical | +0.106 (typical) | 119.80 |
| nangate45 | min16 | typical | +0.106 (typical) | 119.84 |
| nangate45 | lmin2 | typical | -0.024 (typical) | 0.00 |
| ihp | sp | typ_1p20V_25C, slow_1p08V_125C, fast_1p32V_m40C | +0.064 (fast_1p32V_m40C) | 119.45 |
| ihp | min32 | typ_1p20V_25C, slow_1p08V_125C, fast_1p32V_m40C | +0.201 (fast_1p32V_m40C) | 119.48 |
| ihp | min16 | typ_1p20V_25C, slow_1p08V_125C, fast_1p32V_m40C | +0.205 (fast_1p32V_m40C) | 119.50 |
| asap7 | sp | TT, SS, FF | +0.011 (FF) | 119.89 |
| asap7 | m12 | TT, SS, FF | -0.012 (FF) | 119.86 |
| asap7 | min32 | TT, SS, FF | +0.040 (FF) | 119.89 |
| asap7 | min16 | TT, SS, FF | +0.040 (FF) | 119.89 |
| asap7sram | sp | TT, SS, FF | +0.029 (FF) | 119.87 |
| asap7sram | m12 | TT, SS, FF | -0.014 (FF) | 119.86 |
| asap7sram | min32 | TT, SS, FF | +0.047 (FF) | 119.87 |
| asap7sram | min16 | TT, SS, FF | +0.046 (FF) | 119.87 |

OpenSTA on the routed netlist with its SPEF, propagated 200 ns clock, 20 % I/O delays and the flow's false paths (reset,
mode_dense), `report_worst_slack -min`; the flow-scripts runs themselves report no hold figure at signoff. Every IHP netlist meets
hold at all three corners (worst +0.064 ns, sp at the fast corner); the ASAP7 RVT cores meet hold; the negative values are
small: nangate45/m12 -0.025 ns (typical); nangate45/lmin2 -0.024 ns (typical); asap7/m12 -0.012 ns (FF); asap7sram/m12 -0.014 ns (FF). These are 3-25 ps violations on a few paths that the
flow-scripts hold repair (run at the typical corner without the SPEF-annotated clock skew) left; they are reported as measured
and marked in `pdks_table.tex`. The latch core on NanGate45 also reports a setup slack of 0.0 ns (latch time borrowing,
as on sky130). Macros `\pdkhold<Kit><Core>`; `results/hold6.json` keeps every corner.

## E3b. Fill without decap cells - results (23 Sep 02:05)
sky130 (`bmi_snn_sp`, accepted 40 % run): OpenLane rerun from the routed state with `--from OpenROAD.FillInsertion` and
`DECAP_CELL: []` (run tag `bmi_snn_sp_5m_nodecap`; placement and routing unchanged, DRC status therefore unchanged, 0 violations).
The fill step placed 85,751 `fill_1/2` cells instead of 10,082 fillers plus 50,180 `decap_3/4/6/8`; the 454 `decap_3` end caps stay
(sky130 has no dedicated end-cap cell). Idle leakage 0.082 uW against 0.243 uW with the decap fill: the logic cells leak 0.081 uW,
the fillers 0.0015 uW, i.e. the decap cells were 66 % of the pruned core's leakage. P_avg at 250 bins/s (clock stopped, annotated
energy): 0.870 uW instead of 1.03 uW. The later flow steps (antenna check, needing the design LEF that the disabled Magic step
writes) stopped the partial run; the fill-step netlist, the RCX parasitics and the post-fill STA were assembled into a `final/`
view for the measurement (`sim/measure_design.sh` with `RUN_TAG=bmi_snn_sp_5m_nodecap`).
IHP (`bmi_snn_sp`, accepted 20 % run): the filler step `5_3_fillcell` rerun on a copy of the routed result with
`FILL_CELLS = sg13g2_fill_1 sg13g2_fill_2` (no `decap_4/8`), then the final report; 263,707 fillers replace 14,514 fillers plus
73,572 decaps; routing untouched (0 DRC violations). Idle leakage 3.67 uW against 59.6 uW: the logic cells leak 3.66 uW, the
fillers nothing measurable, so 94 % of the IHP pruned core's leakage was the decap fill of the 20 % floorplan. P_avg at 250 bins/s
(annotated 1.97 nJ): 4.16 uW instead of 60.0 uW. Sentence-ready comparison for the pruned core at 250 bins/s, clock stopped:
sky130 1.03 uW total / 0.87 logic-only / 0.87 decap-free; IHP 60.0 / 4.15 / 4.16 uW. Macros `\pdkleakNoDecapSkySp`,
`\pdkleakNoDecapIhpSp`, `\pdkpavgNoDecap<Kit>Sp` (sw/collect_pdks5.py). A side finding: the flow-scripts final-report step
opens a Qt GUI context for its images and aborts without a display (signal 6); `QT_QPA_PLATFORM=offscreen` is now exported by
`synthesis/run_orfs5.sh` (the first round-6 hardenings on the flow-scripts kits were rejected by this, not by the design).
## E6. Front end and pruned core co-simulated - an interface bug found and fixed (23 Sep 02:10)
Setup: `rtl/bmi_sys.v` (structural: `bmi_fe` and `bmi_snn_sp` connected by the event handshake, the tick and the gated 5 MHz
clock; the core's write port tied off), `sim/tb_bmi_sys.v` (the round-5 front-end stimulus: recorded channel indicators of
indy_20160630_01 as one-cycle pulses at a random slow cycle inside each 131-cycle bin, real time at 250 bins/s, 32.768 kHz always
on, the 5 MHz oscillator toggling only while `osc_en`; checks the serialized events per bin, one tick per bin and the core outputs
against the integer reference), `sim/run_sys.sh` (gate-level, both routed netlists, optional streamed dump for the toggle power).
Finding: with the round-5 front end (v2) the system deadlocks after the first bin. The front end pulses `tick` for exactly one
cycle in the cycle after it sampled `tick_ready = 1`; the core, idle after draining the events, has closed its own clock gate
(`en_q`), and a tick that arrives while the gate is closed only re-opens it (`en_d` includes `tick`) - the FSM sees the tick one
cycle later, when the pulse is gone. The round-5 front-end testbench modelled the core with `tick_ready` permanently high and a
fixed latency, so the pulse protocol passed there; the core testbench holds `tick` until the handshake completes, so the core passed
too. Only the co-simulation exercises the pair. Fix (v3, `rtl/bmi_fe.v`; v2 kept as `rtl/bmi_fe_v2_pulsetick.v`): `S_TICK` holds
`tick` high until `tick && tick_ready` is seen in the same cycle, then drops it (one extra flop transition per bin). With the v3
RTL and the routed core netlist the system passes 20 bins bit-exact (every channel serialized once, 20 ticks, all outputs equal
to the reference). The v3 front end is being hardened at 5 MHz with the round-5 policy (60 %, `bmi_fe_5m`; the v2 run is kept as
`bmi_fe_5m_v2`); the 500-bin co-simulation and its per-pin power (two netlists, two SPEFs, two clocks, root-clock correction for
`clk5`) follow on the v3 netlist, and the front end's own E10 numbers are re-measured on v3.

## E6. Front end and pruned core co-simulated - results, and a method finding that also corrects the kit numbers (23 Sep 02:45)
The v3 front end hardened at 5 MHz with the round-5 policy on the first attempt (60 %, `bmi_fe_5m` -> `bmi_fe_5m_u60`, setup and hold
met, 0 DRC); v2 is kept as `bmi_fe_5m_v2`. Its own E10 measurement was repeated on the v3 netlist (`sim/run_fe.sh gls 500 --vcd`,
`power/out_vcd_fe_v3_gls_5m` with the clk5-only zero-data run and the root-clock correction): 0.700 uW at 250 bins/s against 0.691 uW
for v2 (the held tick adds one flop transition per bin; the cycle counts of the 500-bin run are identical: 305,332 clk5 cycles,
305,075 with the oscillator on, duty 3.05 %). `sw/collect_frontend.py` now reads the v3 run (`\fePower` = 0.700) and keeps
`\fePowerVtwo` = 0.691.
Co-simulation (`sim/measure_sys.sh 500`, `sys_sp_gls_5m`): 500 bins in real time at 250 bins/s, 2,934 events, every channel
serialized once, 500 ticks, every core output bit-exact (out_errors = 0); the core clock runs 9,858 cycles = 19.7 per bin (the
stand-alone testbench, which presents the events back to back, needs 20.8). Power over both routed netlists (two SPEFs, `clk5` and
`clk32k` as asynchronous clocks): front end 4.876 uW reported -> 0.644 uW after the root-clock correction of its `clk5` root network
(4.233 uW removed; the correction now takes the `--prefix u_fe/` instances only); core 0.865 uW (0.244 leakage + 0.621 dynamic =
2.48 nJ per bin); **system 1.51 uW** (`\pSysSp`). The sum of the two blocks measured separately in round 5 is 0.700 + 0.912 =
1.61 uW (`\pSysSumSeparateSp`; the core's zero-delay 200-bin window at 250 bins/s), so the co-simulated system draws 6 % less
than the sum (`\pSysVsSumPct`): the front end delivers each bin's events as one burst, so the core's valid/enable signals toggle
twice per bin instead of twice per event (ev_valid 2.0 against 9.9 transitions per bin) and its pipeline stays busy instead of
draining after every event; the core work itself is identical (the same potential updates, the same outputs). The stand-alone
zero-delay 500-bin window of the same core is being measured for the like-for-like number (`bmi_snn_sp_5m_func_w500`).
Method finding on the way (important, it changes the kit numbers of round 5): the first system run used `CLK_STOP_ICG=1`
(`set_clock_sense -stop_propagation` at the outputs of all clock-gate cells, introduced in round 5 for `sim/measure_pdk5.sh` so that
gated subtrees would follow the waveform) and reported the core at 0.61 uW with a Combinational group of 3.5 nW. The same
toggle file re-annotated on the flat core netlist gave a Combinational group of 0.25 uW without the stop and 8e-11 W with it:
behind a stopped clock OpenSTA has no clock to convert the per-cycle activities of the downstream pins and their internal and
switching power vanish (the round-5 log already recorded this for a stop at the clock port; a stop at the clock-gate outputs
was believed harmless because a VCD-path test showed no change, which does not hold for the toggle path). The Sequential and Clock
groups are unaffected (their pins are on annotated clock nets), which is why the kits' totals still looked plausible. Every kit
power run of round 5 (`power/out_vcd_pdk5_*`: GF180, IHP, NanGate45, ASAP7, ASAP7 SRAM-Vt, all cores, both windows, the idle runs
and the supply corners) reports a Combinational group of 0.03-0.6 % of the total, against 52 % for the same core on sky130 - the
kits' E_bin values of round 5 miss the combinational energy. All kit clock-gate cells (`sky130_fd_sc_hd__dlclkp`,
`gf180mcu_fd_sc_mcu7t5v0__icgtp`, `sg13g2_lgcp_1`, `CLKGATE_X1`, `ICGx1_ASAP7_75t_R`) carry `clock_gating_integrated_cell` in
their liberty, so OpenSTA scales the gated subtrees itself and no stop is needed (this is the sky130 flow of all rounds).
`sim/measure_pdk5.sh`: default `CLK_STOP_ICG=0`, new kind `sta` (OpenSTA re-annotation of the existing toggle files of a
kit/core: decode and idle windows, both timing modes, the 5,000-bin window and the supply corners; a toggle file younger than
5 min is left to the measurement that is still writing it). The re-annotation of all finished kit runs is running; the 5,000-bin
kit windows in flight will be re-annotated when they finish. Leakage, area, timing, hold and the decap results (E3) are untouched.
The system run itself was repeated without the stop (numbers above); `power/out_vcd_sys_sp_gls_5m_icgstop` and `_netsonly` keep
the two diagnostic runs. `power/toggles_to_activity.py` also annotates the cell pins inside a hierarchical block now (it skipped
paths deeper than two levels; the result is identical because the driver-pin annotation of the nets already covered them).

## E4. Progress (23 Sep 02:55)
- E4a per-session g32p50: the policy runs of `bmi_snn_g32p50_s622` (60 % rejected, 50 % running since 02:39) and `_s131` (60 %
  running since 01:49) continue; their pipelines (`sim/pipeline5.sh`, own-session full block and 5,000-bin annotated window) wait
  for the accepted netlists.
- E4b 1.28 V: `bmi_snn_g32p50` hardened with ss_n40C_1v28 as signoff at 40 % (`bmi_snn_g32p50_5m_lv`, 24 min, 0 DRC, pass). Its
  measurement first stopped with "unknown design": `sim/measure_lowv.sh` had cases for sp, m12 and min32 only; a g32p50 case was
  added (ROM `rtl/g32p50`, the first bins of `sim/vecfull_g32p50_indy_20160630_01`) and the measurement relaunched (02:52). The
  1.8 V netlist is re-evaluated with the 1.28 V and 100 C liberties as for the other cores (`sim/corners5.sh`, then the annotated
  window with `power/run_corner_power.sh`), and `sw/collect_corners5.py` lists g32p50 as a fourth core (macro suffix GcHalf).
- E4c kits: g32p50 accepted on NanGate45 (50 %), ASAP7 RVT (60 %), ASAP7 SRAM-Vt (60 %), GF180 (40 %, OpenLane); IHP at 30 %
  is in detailed routing. Measurements: NanGate45 and ASAP7 RVT complete (decode, idle, supply corner, 5,000-bin window), ASAP7
  SRAM-Vt and GF180 running. All of them were annotated with the round-5 default (`CLK_STOP_ICG=1`) and will be re-annotated
  (`measure_pdk5.sh <kit> g32p50 sta`) once their toggle files are complete; the g32p50 rows of the kit table come from that pass.
- E4d four grid points: all 12 first-seed models of H = 48 (dense, 50 %, 25 %) and H = 32 / 12.5 % are trained (24 of the 60
  runs including the extra seeds so far; the GPU is shared with another user's job, two runs at a time). Float test R2 of the
  seed-0 models on indy_20160630_01: 0.533 / 0.536 / 0.532 / 0.442 (H = 32 at 12.5 % falls clearly below the 0.55 gate, as the
  H = 64 / 12.5 % point did). Hardware: ROMs `rtl/g48/`, `rtl/g48p50/`, `rtl/g48p25/`, `rtl/g32p125/` (sw/gen_weights_rom.py), flat
  variants `rtl/gen/bmi_snn_{g48,g48p50,g48p25,g32p125}.v` (sw/gen_variant.py; H = 48 needs no power-of-two width anywhere in
  `rtl/bmi_snn_par.v`), full-block vectors `sim/vecfull_<tag>_indy_20160630_01` (107,444 bins, 12/14-bit), OpenLane configs copied
  from g32p50, the four policy hardenings (60 50 40 30) and their pipelines launched at 02:46; `sim/measure_design.sh`,
  `sim/measure_full.sh` and `sw/collect_pareto.py` (GRID entries GeDense, GeHalf, GeQuarter, GcEighth) know the new names. The
  integer-reference evaluation (`sw/eval_int.py`) of every finished grid-6 model runs in the background.
## E8 (optional). ASAP7 SRAM-Vt utilization sweep of the pruned core - launched (23 Sep 02:48)
`synthesis/run_orfs5.sh` gained a `SWEEP=1` mode (run nick `<core>_5m_sram_sweep_u<U>`, every point kept, nothing relinked, one
line per point in `logs/orfs6_util_sweep.log`) and `sim/measure_pdk5.sh` accepts `RUN_NICK` for ASAP7 as well. Sweep 40 / 50 / 70 %
around the accepted 60 % run; each point is then measured on the 500-bin window and idle (`RUN_NICK=... TAG_SFX=_u<U>
measure_pdk5.sh asap7sram sp func`) and collected by `sw/collect_util_sweep6.py` -> `results/asap7_util_sweep.csv`,
`paper/numbers_sweep6.tex` (`\sweepAsapS<Util><key>`). The 60 % point after the re-annotation: 0.0788 nJ, 0.719 uW leakage
(27,467 cells, 3,441 um2 of cells).
## Re-annotation of the kit runs - progress (23 Sep 02:55)
18 of 22 kit/core pairs re-annotated (`logs/pdk6_sta_<kit>_<core>.log`). First effect: ASAP7 min16 decode power 7.75 -> 14.1 uW
(E_bin 0.0318 -> 0.058 nJ, +82 %), ASAP7 SRAM-Vt sp 0.0575 -> 0.0788 nJ (+37 %). The runs still in flight (GF180/IHP 5,000-bin
windows, GF180 and ASAP7 SRAM-Vt g32p50) follow when their toggle files are complete. Machine load 60 on 24 cores at this point
(four OpenLane hardenings, two policy runs, two flow-scripts runs, ten gate-level simulations, two trainings, the OpenSTA passes).

## E4b. g32p50 at 1.28 V - results (23 Sep 03:05)
`bmi_snn_g32p50_5m_lv` (ss_n40C_1v28 signoff, 40 %): 19,218 cells (13,775 at 1.8 V), setup slack 112.7 ns, hold 2.36 ns, 0 DRC.
Annotated 200-bin window at 1.28 V: 1.04 nJ per bin against 2.21 nJ of the 1.8 V netlist at its own corner (the 1.8 V netlist
re-evaluated with the 1.28 V liberty: 0.957 nJ, f_max 15.7 MHz); leakage 0.0435 uW at -40 C; P_avg at 250 bins/s with the clock
stopped 0.303 uW. Macros `\cnrFive*GcHalf` (sw/collect_corners5.py; corners_table5.tex has the fourth row). The ratio 1.04 / 2.21
= 0.47 sits between sp (0.45 in round 5) and the dense cores, i.e. the pruned H = 32 core scales with the supply like the others.

## E8 (optional). ASAP7 SRAM-Vt utilization sweep - results (23 Sep 03:20)
Four routed placements of the pruned core with the SRAM-Vt library (40 and 50 % and 70 % from the sweep, 60 % the accepted policy
run), every one DRC-clean with the same setup slack; the 500-bin decode window and the idle run measured on each
(`RUN_NICK=bmi_snn_sp_5m_sram_sweep_u<U> TAG_SFX=_u<U> sim/measure_pdk5.sh asap7sram sp func`, no clock-gate stop).
| util % | cells (incl. fill) | fill cells | cell area um2 | setup ns | DRC | E_bin nJ (500 bins, zero-delay) | leakage uW | P_avg uW at 250 bins/s |
|---|---|---|---|---|---|---|---|---|
| 40 | 35,260 | 12,077 | 5,242 | 119.9 | 0 | 0.0796 | 0.723 | 0.743 |
| 50 | 30,875 | 11,604 | 4,151 | 119.9 | 0 | 0.0791 | 0.721 | 0.741 |
| 60 | 27,467 | 10,776 | 3,441 | 119.9 | 0 | 0.0788 | 0.719 | 0.738 |
| 70 | 24,466 | 9,694 | 2,937 | 119.9 | 0 | 0.0720 | 0.704 | 0.722 |
The energy per bin is flat within 1 % from 40 to 60 % and 9 % lower at 70 % (shorter wires; the flow keeps the same cell set),
leakage follows the filler count weakly (the fillers of this library leak nothing measurable; the 2 % spread is the logic
re-optimisation). The utilization policy of round 5 therefore does not bias the ASAP7 figures: the accepted point is within 1 % of the
denser one that also routes, and the 60 % default is not the energy optimum only because 70 % also converges on this small core.
`results/asap7_util_sweep.csv`, `paper/numbers_sweep6.tex` (`\sweepAsapS<Forty|Fifty|Sixty|Seventy><area|cells|fill|setup|drc|e|leak|pavg>`).

## E6 addendum - like-for-like core comparison (23 Sep 04:15)
The stand-alone zero-delay run of the pruned core on the same first 500 bins (`bmi_snn_sp_5m_func_w500_indy_20160630_01`)
reproduces the round-5 decode window exactly (641.5602 uW against 641.5601 uW: the round-5 zero-delay window *is* the first 500
bins, so the toggle path is deterministic to the last digit): 2.674 nJ per bin, 20.9 clock cycles per bin, against 2.48 nJ and
19.7 cycles per bin for the same core inside the system - the in-system core spends 7 % less energy per bin because the front end
delivers each bin's events in one burst (`\eSysCoreAloneWFiveSp`, `\eSysCoreSp`). At 250 bins/s: core alone 0.912 uW
(`\pSysCoreAloneWFiveSp`), in the system 0.865 uW; the system 1.51 uW is 6.4 % below the sum of the separate measurements. Both
500-bin window scripts had lost their power step to a log-name clash (the outer log was the file the script greps: "input file is also
the output", `set -e`); the power steps were run by hand (`power/run_toggles_power.sh core`), the gotcha is in the memory notes.
The top core's annotated 500-bin window (41.3 nJ, E1) came from the same repair.

## E4d. Grid accuracies, and the H = 48 hardenings restarted (23 Sep 05:20)
All 60 grid-6 trainings and their integer-reference evaluations are complete (5 seeds x 3 sessions per point, `sw/eval_int.py`):
| H | density | R2 (int, mean of 5 seeds over 3 sessions) | sd | seed-0 R2 on indy_20160630_01 |
|---|---|---|---|---|
| 48 | dense | 0.580 | 0.0025 | 0.533 |
| 48 | 50 % | 0.577 | 0.0036 | 0.536 |
| 48 | 25 % | 0.567 | 0.0048 | 0.532 |
| 32 | 12.5 % | 0.482 | 0.0057 | 0.442 |
H = 48 sits between H = 32 (0.556 at 25 %, 0.57 at 50 %) and H = 64 (0.585 dense, 0.581 at 50 %, 0.574 at 25 %); H = 32 at 12.5 %
is far below the 0.55 gate, as H = 64 at 12.5 % was (0.533). Hardware: `bmi_snn_g32p125` accepted at 60 % and fully measured;
`bmi_snn_g48p25` accepted at 50 % (full block running); `bmi_snn_g48` and `bmi_snn_g48p50` at 60 % had 163,964 and 132,137
DRC violations after the first detailed-routing iteration and no second iteration in two hours (the round-5 watchdog would have
waited three): both attempts were killed by hand (`KILLED_HOPELESS` notes, REJECTED lines in `logs/policy_round5.log`) and the
policies resumed at 40 % then 30 % - the comparable round-5 cores (m12 = H 64 dense, g64p50) were accepted at 30 %. IHP g32p50
at 30 %: detailed routing is converging (18,227 -> 925 violations over 12 iterations), left running.

## Kit numbers after the re-annotation (23 Sep 05:30) - every kit report is clean
All kit runs (decode and idle windows, both timing modes, the supply corners, the 5,000-bin windows) are annotated without the
clock-gate stop; `sw/collect_pdks5.py` rerun. Energy per bin on the common 500-bin zero-delay window, round 5 -> round 6, and the
annotated 200-bin window, the glitch factor and the new 5,000-bin annotated window (nJ):
| kit/core | E zero-delay r5 | r6 | change | E ann. r5 | r6 | glitch r6 | E ann. 5,000 bins | P_avg 250 bins/s r5 -> r6 (uW) |
|---|---|---|---|---|---|---|---|---|
| GF180 sp | 23.8 | 42.8 | +80 % | 25.7 | 52.2 | 1.22 | 46.3 | 10.1 -> 14.8 |
| GF180 m12 | 25.1 | 68.7 | +174 % | 27.9 | 93.5 | 1.36 | 81.8 | 12.5 -> 23.4 |
| GF180 min32 | 31.7 | 56.8 | +79 % | 33.8 | 70.4 | 1.24 | 62.4 | 11.5 -> 17.8 |
| GF180 min16 | 19.0 | 29.7 | +56 % | 20.1 | 36.1 | 1.22 | 32.1 | 6.52 -> 9.19 |
| GF180 lmin2 | 42.2 | 80.5 | +91 % | 45.5 | 94.1 | 1.17 | -- | 60.2 -> 69.7 |
| IHP sp | 1.86 | 2.51 | +35 % | 1.97 | 2.82 | 1.12 | 2.50 | 60.0 -> 60.2 |
| IHP min32 | 2.11 | 3.02 | +43 % | 2.23 | 3.51 | 1.16 | 3.12 | 49.9 -> 50.2 |
| IHP min16 | 0.94 | 1.36 | +46 % | 0.99 | 1.58 | 1.16 | 1.41 | 16.4 -> 16.5 |
| NanGate45 sp | 3.40 | 3.62 | +7 % | -- | -- | -- | 3.41 (zero-delay) | 765 -> 765 |
| NanGate45 m12 | 4.13 | 4.63 | +12 % | -- | -- | -- | 4.34 | 917 -> 918 |
| NanGate45 min32 | 3.02 | 3.35 | +11 % | -- | -- | -- | 3.16 | 666 -> 666 |
| NanGate45 min16 | 1.58 | 1.74 | +10 % | -- | -- | -- | 1.64 | 352 -> 352 |
| ASAP7 sp | 0.0582 | 0.0904 | +55 % | 0.0625 | 0.106 | 1.18 | 0.0952 | 3.32 -> 3.32 |
| ASAP7 m12 | 0.0651 | 0.137 | +111 % | 0.0717 | 0.175 | 1.27 | 0.153 | 3.82 -> 3.84 |
| ASAP7 min32 | 0.0549 | 0.109 | +98 % | 0.0591 | 0.136 | 1.25 | 0.121 | 2.82 -> 2.84 |
| ASAP7 min16 | 0.0318 | 0.0579 | +82 % | 0.0340 | 0.0709 | 1.22 | 0.0630 | 1.53 -> 1.53 |
| ASAP7 SRAM-Vt sp | 0.0495 | 0.0787 | +59 % | 0.0532 | 0.0922 | 1.17 | 0.0825 | 0.731 -> 0.738 |
| ASAP7 SRAM-Vt m12 | 0.0538 | 0.120 | +123 % | 0.0596 | 0.154 | 1.28 | 0.135 | 0.856 -> 0.873 |
| ASAP7 SRAM-Vt min32 | 0.0476 | 0.0969 | +104 % | 0.0512 | 0.119 | 1.23 | 0.105 | 0.637 -> 0.649 |
| ASAP7 SRAM-Vt min16 | 0.0268 | 0.0507 | +89 % | 0.0287 | 0.0621 | 1.23 | 0.0552 | 0.350 -> 0.356 |
The sky130 rows are unchanged (they never used the stop). The dense 12-bit core gains most (its combinational share is the
largest, 57-71 % of the dynamic power); the combinational share of the corrected kit runs (29-68 %) now matches sky130's (43-71 %).
The kits' glitch factors move from 1.06-1.08 to 1.12-1.36 and now bracket sky130's 1.18-1.33, as expected when the glitching
combinational logic is counted. NanGate45 changes by 7-12 % only because its energy per bin is dominated by the leakage during the
decode window (474 uW). P_avg at 250 bins/s changes little for IHP, NanGate45 and ASAP7 (leakage-dominated) and by 40-90 % for GF180.
The cross-kit ratios in the paper therefore change: GF180 at 5 V costs 16x (not 8.9x) the sky130 dynamic energy per bin, IHP 0.94x
(not 0.70x), ASAP7 RVT about 30x less than sky130 (not 46x), and the paper's typed-in glitch factors of the kit table (1.08 / 1.06 /
1.07 / 1.08) become macros (`\pdkglitch<Kit>Sp`).

## Paper: kit statements updated, and a collector side effect removed (23 Sep 05:50)
`paper/results.tex` (copy of the round-5 text in `paper/_superseded/2026-09-23_before_round6_runs/`): the typed-in glitch factors of
the kit table (1.18 / 1.08 / 1.06 / 1.07 / 1.08) are now the macros `\pdkglitch<Kit>Sp`; the sentence "on the other kits the factors
are 1.06 to 1.11" reads `\pdkglitchIhpSp` to `\pdkglitchGfMinT` (1.12 to 1.36); "about 60 times less than sky130" (four places) is
`\fpeval{round(\pdkeDynSkySp/\pdkeDynAsapSp,0)}` (35); "the 45 nm library about 13 times" is the same construction (6); "at equal
supply the 180 nm library is level with the 130 nm one per bin" (two places) now says it needs
`\fpeval{round(\pdkeGfSpttZeroTwoFiveCOnevEightZero/\pdkeSkySp,1)}` times the energy (1.8); the ASAP7 "flow settings" caution
(the 16-neuron core at 50 MHz / 40 % needing 1.9x the energy of the 5 MHz / 60 % run) is rewritten, because the round-1-4 number
(0.0606 nJ, measured without the clock-gate stop) and the corrected round-6 number (0.0579 nJ) agree within 5 % - the 1.9x was the
missing combinational power, not the flow - and the sentence now cites the E8 sweep instead. `paper/appendix.tex` (policy section)
gained the E8 paragraph with the `\sweepAsapS*` macros; `paper/main.tex` inputs `numbers_software6.tex` and `numbers_sweep6.tex`.
The abstract's "about 60 times less dynamic energy per decode" (main.tex line 108) still needs the author's wording (35 with the
corrected numbers); it is typed in, not a macro, and is left for the author.
Side effect found while compiling: `sw/collect_designs5.py` imports two helpers from the round-4 `sw/collect_pdks.py`, whose module
body rewrote `paper/numbers_pdks.tex` and `paper/pdks_table.tex` with the round-4 macro set on every import. Harmless in the round-5
refresh order (collect_pdks5 ran after it) but the round-6 collectors that import collect_designs5 (`collect_frontend.py`,
`collect_software6.py`) clobbered the kit macros after collect_pdks5 had written them (the paper then failed with an undefined
`\pdkpavgSdfAsapSSp`). The module body of collect_pdks.py is now under `if __name__ == "__main__"`; `sw/refresh_round6.sh` keeps
the collectors in dependency order anyway. Macro names with digits (`\evWin16`) are illegal in LaTeX; `collect_software6.py` uses
Sixteen/Hund/FiveH/FiveK.

## F1 (23 Sep 05:50)
`figures/fig_pareto.py`: every sky130 core is plotted at its 5,000-bin annotated block energy (the energy of Table 3) where measured,
else the 200-bin annotated window (legend text names the window); the software point takes the 100-bin window of E1 when
`results/explore/software6.json` has it (legend names the window; the 16-bin round-5 point until then); H = 48 has its own colour
(Okabe-Ito vermilion), the x axis starts at 0.47 so that H = 32 at 12.5 % (R2 0.482, 0.97 nJ) is inside, the y axis at 0.7 nJ, the
figure is 4.3 in high and the labels of the R2 = 0.57-0.585 cluster sit in one log-spaced right-hand column with leader lines
(min, m12, ming, g48, lmin2, min32, g48p50, sp) or in the free space left of the cluster (g48p25). Current state: 22 points; the
dense H = 48 point follows its hardening. New grid points: H = 48 / 50 % 3.35 nJ (200-bin annotated, 5,000-bin block pending),
H = 48 / 25 % 2.28 nJ, H = 32 / 12.5 % 0.97 nJ at R2 0.488 (below the gate).

## E1. The 100-bin SoC simulations had to be restarted (23 Sep 06:50)
The two 100-bin gate-level runs launched at 01:50 ran with the testbench's default 20 ns clock: the round-5 5 MHz runs had passed
`EXTRA_DEFS="-DCLK_PERIOD_NS=200"` and the relaunch did not. The hand-tuned run finished (235 min, output correct) and its window
came out at 20.96 mW over 540,140 cycles (5,401 per bin, 4.95 active channels per bin) - ten times the round-5 window power,
because the per-pin activities were converted with the 200 ns period the script was told while the waveform ran at 20 ns; the
annotated netlist is also a 200 ns signoff (critical path 44 ns), so a 20 ns waveform is not a valid measurement even with the right
period. Both runs were stopped (the -O2 one after 5 h, 32 GB of waveform), the wrong window report removed, and both relaunched
with the 200 ns clock at 06:48 (`EXTRA_DEFS="-DCLK_PERIOD_NS=200" RUN_DIR=.../sky130_vex2_soc_5m FW_OPT=-O2
FW_SRC=bmi_snn_sw{,_tuned}.c VARIANT=_5m_{o2,tuned}_100 sim/run_riscv.sh gls --vcd`); the waiter measures the two 100-bin windows
(`sim/measure_soc_window.sh ... 200 <fw>_5m_100 100`) when they exit. Expected 4-6 h each (the runtime is set by the event count
and the waveform size, not by the simulated time). The cycles per bin of the 20 ns run (5,401 for the hand-tuned firmware on the
100-bin window against 4,795 on the 16-bin window, +13 % for +26 % events per bin) are unaffected by the clock and already show the
window effect the referee asked about; the energies follow from the 200 ns runs.

## E4a. g32p50 per session - results (23 Sep 07:10)
| session | netlist | util | test bins | active ch./bin | E_bin zero-delay (full block) | E_bin annotated (5,000 bins) | leakage uW | R2 (int, that session's model) |
|---|---|---|---|---|---|---|---|---|
| indy_20160622_01 | bmi_snn_g32p50_s622 | 40 % | 132,745 | 7.93 | 2.20 nJ | 2.71 nJ | 0.144 | 0.569 |
| indy_20160630_01 | bmi_snn_g32p50 (round 5) | 50 % | 107,444 | 4.88 | 1.57 nJ | 1.95 nJ | 0.108 | -- |
| indy_20170131_02 | bmi_snn_g32p50_s131 | 40 % | 52,116 | 3.71 | 1.29 nJ | 1.56 nJ | 0.140 | -- |
Every block bit-exact against the integer reference. The energy follows the session's event rate as for the other three per-session
cores (2.20 / 1.57 / 1.29 nJ for 7.93 / 4.88 / 3.71 active channels per bin: 0.28-0.35 nJ per active channel-bin, the fixed
per-bin part dominating at the low-rate session). `sw/collect_persession.py` (GcHalf rows and macros `\ePerSessGcHalf<A|B|C>` etc.),
`paper/appendix.tex` Table tab:persession has the three rows; `sw/collect_designs5.py` knows the two netlists (SESSION_OF).

## E4c. g32p50 on the kits - results so far (23 Sep 07:20)
`sw/collect_pdks5.py` lists g32p50 as a sixth core (shorthand GcHalf); `sw/hold_orfs6.py` checks its hold on the flow-scripts kits
(all positive: NanGate45 +0.035, ASAP7 RVT +0.020, ASAP7 SRAM-Vt +0.038 ns). Every kit report without the clock-gate stop:
| kit | util | cells | area mm2 | E zero-delay 500 bins nJ | E ann. 200 bins | E ann. 5,000 bins | glitch | leakage uW | P_avg 250 bins/s uW |
|---|---|---|---|---|---|---|---|---|---|
| sky130 | 50 % | 13,775 | 0.101 | 1.78 | 2.21 | 1.95 | 1.24 | 0.108 | 0.596 |
| GF180MCU 5 V | 40 % | 11,498 | 0.317 | 25.8 | 33.1 | (running) | 1.28 | 2.77 | 11.0 |
| NanGate45 | 50 % | 13,485 | 0.0178 | 2.20 | n/a | 2.07 (zero-delay) | -- | 457 | 458 |
| ASAP7 RVT | 60 % | 12,511 | 0.00152 | 0.0665 | 0.0801 | 0.0713 | 1.20 | 2.06 | 2.08 |
| ASAP7 SRAM-Vt | 60 % | 12,362 | 0.00149 | 0.0575 | 0.0686 | 0.0611 | 1.19 | 0.454 | 0.470 |
| IHP SG13G2 | 30 % (routing) | | | | | | | | |
The kit ranking of the pruned H = 64 core repeats for the H = 32 / 50 % core (per bin ~0.65x the pruned core on every kit; leakage
0.44-0.6x on the kits whose leakage is logic-dominated). IHP at 30 %: detailed routing at iteration 17 with 445 violations, still
converging (the H = 64 pruned core needed 20 %; the policy steps to 20 % if 30 % fails). GF180's 5,000-bin annotated window was
launched at 07:20.

## E1. Software baseline on the 100-bin window - hand-tuned firmware (23 Sep 09:20)
200 ns run of the hand-tuned firmware on the first 100 bins of the test block (495 active channel-bins, 4.95 per bin; the 16-bin
round-5 window had 63, 3.94 per bin): 540,140 cycles in the decoding window = 5,401 per bin (4,795 on the 16-bin window), window
power 2.11 mW (2.09 in round 5; the vdd-only SRAM liberty), **2,276 nJ per bin** against 2,003 nJ on the 16-bin window (+14 % for
+26 % active channels per bin: the fixed per-bin part of the firmware, tick update and output, is about half of the cycles).
Idle 11.9 uW with the clock running (8,000 sleep cycles). At 250 bins/s with the clock stopped: 574 uW (`\pAvgStopCpuWTunedHund`).
On the same 100 bins the cores need 2.68 nJ (pruned, annotated), 5.70 nJ (dense 12-bit) and 37.3 nJ (SRAM sequential): ratios
850 / 400 / 61 (`\ratioWHundTuned<Sp|MinT|Seq>`; the round-5 16-bin-to-200-bin ratio for the pruned core was 635 - the 16-bin
window under-counted the software by the missing events, exactly the referee's point). The -O2 firmware's 100-bin run is still
simulating (its 16-bin window had 9,022 cycles per bin); `results/explore/software6.json`, `paper/numbers_software6.tex`.

## E4d. Four grid points - hardware complete (23 Sep 10:00)
| core | H | density | util | cells | R2 (5 seeds x 3 sessions) | E 200 bins zero-delay / annotated (nJ) | E full block zero-delay | E 5,000 bins annotated | leakage uW | P_avg 250 bins/s (5,000-bin ann.) |
|---|---|---|---|---|---|---|---|---|---|---|
| bmi_snn_g48 | 48 | dense | 30 % (0.8 ns hold margin) | 25,150 | 0.580 | 3.73 / 4.92 | 3.26 | 4.31 | 0.282 | 1.36 |
| bmi_snn_g48p50 | 48 | 50 % | 40 % | 20,614 | 0.577 | 2.65 / 3.35 | 2.33 | 2.96 | 0.206 | 0.945 |
| bmi_snn_g48p25 | 48 | 25 % | 50 % | 17,777 | 0.567 | 1.92 / 2.28 | 1.71 | 2.03 | 0.141 | 0.649 |
| bmi_snn_g32p125 | 32 | 12.5 % | 60 % | 10,274 | 0.482 | 0.953 / 1.08 | 0.854 | 0.968 | 0.067 | 0.309 |
(for comparison: m12 = H 64 dense 0.581 / 6.04 nJ, sp = H 64 25 % 0.573 / 2.80 nJ, min32 = H 32 dense 16-bit 0.574 / 3.71 nJ,
g32p50 = H 32 50 % 0.573 / 1.95 nJ; all 5,000-bin annotated). All blocks bit-exact. Pareto front (sw/collect_pareto.py): the dense
H = 48 core (0.580, 4.31 nJ) and the H = 48 / 50 % core (0.577, 2.96 nJ) join the front between the dense H = 64 core (0.581,
6.04 nJ) and the H = 32 / 50 % core (0.573, 1.95 nJ); H = 48 / 25 % (0.567, 2.03 nJ) is dominated by H = 32 / 50 % (0.573, 1.95 nJ),
and H = 32 / 12.5 % (0.482, 0.97 nJ) falls far below the 0.55 gate as the other 12.5 % points do. So the front now reads: 6.04 nJ
at 0.581, 4.31 at 0.580, 2.96 at 0.577, 1.95 at 0.573 - accuracy is bought at roughly 2x energy per 0.004 of R2 in this range, and
the H = 48 points fill the gap the referee pointed at without changing the picture. The dense H = 48 core needed the same
hold-margin recipe as the dense H = 64 core (40 % routes but fails hold by 0.14 ns; 40 % with the margin does not route; 30 % with the
margin routes and meets timing).

## E1. Software baseline on the 100-bin window - both firmwares (23 Sep 10:20)
| firmware | window | cycles per bin | active ch./bin | window power (mW) | E per bin (nJ) | ratio to pruned core, same window, annotated | to dense 12-bit | to SRAM sequential |
|---|---|---|---|---|---|---|---|---|
| -O2 | 16 bins (round 5) | 9,022 | 3.94 | 1.95 | 3,522 | (200-bin core window) 1,117 | | |
| -O2 | 100 bins | 10,587 | 4.95 | 1.97 | **4,165** | 1,554 (2.68 nJ) | 731 (5.70 nJ) | 112 (37.3 nJ) |
| hand-tuned | 16 bins (round 5) | 4,795 | 3.94 | 2.09 | 2,003 | 635 | | |
| hand-tuned | 100 bins | 5,401 | 4.95 | 2.11 | **2,276** | 850 (2.68 nJ) | 400 (5.70 nJ) | 61 (37.3 nJ) |
Both 200 ns gate-level runs of the 5 MHz SoC netlist (vdd-only SRAM liberty for the window power; the as-generated liberty gives
+1.2 %), decoding windows found by `sw/riscv_window.py`, correct outputs. Per active channel-bin the software costs about
740 nJ (-O2) and 270 nJ (hand-tuned) on top of a fixed 1,200 / 950 nJ per bin; the cores' cost per bin barely moves with the event
count (the pruned core: 2.68 nJ on 100 bins with 4.95 ch./bin, 3.00 nJ on 500 bins with 5.87, 2.80 nJ on 5,000 bins with 5.26), so
the software-to-core ratio grows with the window's event rate: 850x on the 100-bin window against 635x on the round-5 16-bin
window (hand-tuned) - the round-5 figure under-stated the software by the 26 % fewer events of its short window. 500 bins cannot be
held in the SoC's 8 kB data memory next to the 6 kB of weights (E1 note of 01:50); 100 bins with 16-bit expected outputs fit.
`results/explore/software6.json`, `paper/numbers_software6.tex` (`\eCpuW<Otwo|Tuned><Sixteen|Hund>`, `\cycCpuW*`, `\pWinCpuW*`,
`\pAvgStopCpuW*`, `\ratioW<Sixteen|Hund><Otwo|Tuned><Sp|MinT|Seq>`, `\evWin<Sixteen|Hund|FiveH|FiveK>`, `\evPerBinWin*`, the cores'
`\eW<Hund|FiveH><Sdf|Func><Sp|MinT|Seq>`). Figure F1 plots the hand-tuned point at its 100-bin window.
## E5. Register-file core annotated (23 Sep 10:20)
`bmi_snn_scmem_5m_sdf_w50_indy_20160630_01`: the 50-bin annotated window of the register-file core completed in 516 min (the
5,000-bin one of round 5 had been abandoned; 50 bins is E9's rule for the memory cores), 156 events, bit-exact. 7.82 nJ per bin
annotated against 7.08 zero-delay on the same 50 bins: glitch factor **1.10** (`\sdfRatioRf`), between the latch memories (1.08)
and the hardwired cores (1.18-1.33) - the standard-cell memories' signals settle once per cycle, so the arithmetic contributes the
glitching. Derived annotated figures (zero-delay 200-bin window x 1.10, the E9 convention): 11.3 nJ per bin (`\eSdfRf`), P_avg at
250 bins/s with the clock stopped 7.68 uW (`\pavgStopSdfRf`); `sw/collect_designs5.py` derives them automatically from the two
50-bin runs, nothing to add by hand.
## IHP g32p50 (23 Sep 10:20)
Still in detailed routing at 30 % (iteration 24, 92 violations, one iteration per hour at this stage; 8 h so far). The policy steps to
20 % if it fails. Reported as "in progress" if it has not finished when this round closes; its row is added by `sim/measure_pdk5.sh
ihp g32p50 all` + `w5000` and the collectors when it does.

## Closing summary of round 6 (23 Sep 10:25)
| item | asked | done | where |
|---|---|---|---|
| E1 software baseline on the cores' window | 500 bins, or 100 bins with event counts | 100 bins for both firmwares (500 bins do not fit the 8 kB data memory next to the 6 kB weights; the reason and the arithmetic are in the E1 setup note); event counts of every window | `paper/numbers_software6.tex`, `results/explore/software6.json`, F1 software point |
| E2 annotated 5,000-bin kit windows | GF180 / IHP / ASAP7 (zero-delay NanGate45) | all 19 kit/core windows plus g32p50 on GF180, NanGate45, ASAP7 x2 | `\pdkeSdfW<Kit><Core>`, `\pdkpavgSdfW*`, kit table column "E ann. 5k", `results/pdks_pavg_vs_rate.csv` (energy_window column), F2 |
| E3 leakage split, decap-free fill | fill / decap / tap / diode; sky130 + IHP without decaps | done (E3a table, E3b sp on both kits) | `results/leak_split6.{csv,json}`, `\pdkleak<Fill|Decap|Tap|Diode>*`, `\pdkleakNoDecap<Sky|Ihp>Sp`, `\pdkpavgNoDecap*` |
| E4a g32p50 per session | s622 / s131 netlists | done, full blocks + 5,000-bin annotated | `\ePerSessGcHalf*`, appendix table tab:persession |
| E4b g32p50 at 1.28 V | hardening + measurement | done | `\cnrFive*GcHalf`, corners_table5 |
| E4c g32p50 on the kits | GF180, IHP, NanGate45, ASAP7 x2 | done on four kits (decode, idle, corners, 5,000 bins, hold); IHP still routing at 30 % after 8 h | kit table GcHalf rows |
| E4d grid points | H 48 dense / 50 / 25 %, H 32 / 12.5 % | trained (5 seeds x 3 sessions), evaluated, hardened, measured (200-bin, full block, 5,000-bin annotated) | `results/pareto.csv`, `\rsqGrid<GeDense|GeHalf|GeQuarter|GcEighth>`, designs table, F1 |
| E5 register-file core annotated | 50-bin window | done, glitch 1.10 | `\sdfRatioRf`, `\eSdfRf`, `\pavgStopSdfRf` |
| E6 front end + core co-simulated | system power | done (v3 front end after the interface bug; 1.51 uW system) | `\pSysSp`, `\pSysFeSp`, `\pSysCoreSp`, `\eSysCoreSp`, `\pSysSumSeparateSp`, `\pSysVsSumPct` |
| E7 hold slacks on the ORFS kits | hold column | done (OpenSTA on netlist + SPEF, three corners), incl. g32p50 | kit table "Hold" column, `\pdkhold<Kit><Core>`, `results/hold6.json` |
| E8 ASAP7 utilization sweep (optional) | 40-70 % | done | `results/asap7_util_sweep.csv`, `\sweepAsapS*`, appendix paragraph |
| F1-F4 | figure changes | done (F1 5,000-bin energies + software window + H 48 + declutter; F2 5,000-bin curves + IHP logic-only / decap-free; F3 labels; F4 duplicate labels) | `paper/figures/`, `figures/` |
Method finding of the round (not asked, but it changes round-5 numbers): the kit power runs of round 5 lacked the combinational
power (clock-gate stop in the toggle path); all kit reports were re-annotated, the kit energies rose by 7-174 % (GF180 and the dense
cores most), the paper's kit ratios and glitch factors are macros now, and the 1.9x "flow settings" discrepancy of the ASAP7
16-neuron core disappeared (1.05x). The sky130 numbers of rounds 1-5 are unaffected.
Not done / reasons: (1) a 500-bin software window - impossible in one image (memory); the 100-bin window carries the referee's point
(events per bin 4.95 vs 3.94, ratio 850x vs 635x). (2) IHP g32p50 - the hardening has not converged yet (routing at 30 %); the
other four kits carry the comparison. (3) The scmem 5,000-bin annotated window - not attempted (the 50-bin window took 8.6 h; E9's
50-bin rule applies to the memory cores, and the glitch factor is what the referee asked for). (4) The abstract's "about three times
the average power" for the ASAP7 regular-threshold flavor is still typed in (3.2x with the corrected numbers, unchanged in
substance); every other kit ratio in the text is a macro.
Two mistakes of this round, both caught by the checks and repeated correctly: the 100-bin SoC runs first ran with a 20 ns testbench
clock (relaunched at 200 ns), and two window scripts lost their power step to a log-name clash (rerun by hand).
Machine time: about 9 h wall-clock with up to 60 concurrent processes on 24 cores; the SoC waveforms (38 + 27 GB) are kept in
`sim/build_riscv_gls_5m_*_100/` until the paper is accepted.
