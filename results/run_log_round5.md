# Run log, round 5 (experiments_round5.md)

Started 2026-09-19. Repository `sky130-snn-bmi`; SoC in `sky130-vex2-soc` (`../skywater`). Previous versions of every replaced
generated file are in `paper/_superseded/2026-09-19_before_round5/`. All runs: OpenLane 2.3.10 (Nix) with sky130A `sky130_fd_sc_hd`
unless stated; OpenSTA 2.6.0 per-pin power (`read_power_activities -vcd`) on the routed netlist with the nominal SPEF; Icarus Verilog
(oss-cad-suite) gate-level simulation, zero-delay ("functional", cell models with `#1` unit delay) and SDF-annotated (typical-corner
cell delays, interconnect delays and timing checks removed by `sim/sdf_sanitize_for_icarus.py`).

## E1. Common clock and utilization policy

### Clock choice (arithmetic)
Real-time constraint: average cycles per bin x period < 4 ms. Cycles per average bin (indy_20160630_01 window, 50 MHz results):
compiler-generated software 9,030 (the slowest implementation), hand-tuned software 4,795, dense mode 1,635, sequential SRAM core 185,
parallel cores 20 to 25. Bound from the software: 9,030 / 4 ms = 2.26 MHz. Chosen clock: **5 MHz (200 ns)** for every design and every
kit (below half the bin for the software: 1.81 ms per average bin at -O2, 0.96 ms hand-tuned, 0.33 ms dense mode, 37 us sequential core,
4 to 5 us parallel cores). 2.5 MHz would need input buffering for bins with many events in software; not used.

### Utilization policy
Start at 60 % core utilization (`FP_CORE_UTIL`, `PL_TARGET_DENSITY_PCT` = utilization + 10); if detailed routing does not converge
(`route__drc_errors` > 0) or timing is not met at a signoff corner, step down by 10 % and re-run. Recorded per design below.
Macro designs (`bmi_snn_top`, `bmi_snn_topg`, the SoC) use an absolute die: utilization is reported as standard-cell area over the
core area left by the macro (documented per design).

### Flow configuration (all sky130 cores)
`config_5mhz.yaml` generated from each design's `config.yaml` by `synthesis/harden_policy.sh`: `CLOCK_PERIOD: 200`, utilization per
policy, `SYNTH_STRATEGY` left at the OpenLane default (AREA 0; the 50 MHz runs of the 64-lane hardwired cores and the latch cores used
DELAY 0), `DRT_OPT_ITERS` at the default 64, hold margins as before. Signoff corners as before (nom/min/max x tt_025C_1v80,
ss_100C_1v60, ff_n40C_1v95). Simulation: `CLK_NS=200`; power: `PERIOD_NS=200`.

(results follow)

### Policy amendment (2026-09-19 07:27)
The first runs at 60 % and 50 % utilization failed in detailed placement (OpenROAD DPL-0036) for the pruned and the 12-bit
64-lane cores: OpenLane's heuristic antenna-diode insertion (`RUN_HEURISTIC_DIODE_INSERTION`) adds several thousand diode cells
after global placement with zero cell padding, and legalization no longer finds room at these densities. The 50 MHz runs kept the
diodes because they were placed at 22 to 40 %. For every round-5 hardening the heuristic insertion is off and diodes are placed on
the input ports only (`DIODE_ON_PORTS: in`); no antenna check is run in either case (as before). The 16-neuron core was hardened
both ways at 60 % (run tags `bmi_snn_min16_5md_u60` with heuristic diodes, `bmi_snn_min16_5m_u60` without) so that the effect of the
diodes on energy and leakage is quantified (see the E1 table).

### SoC (sky130-vex2-soc) at 5 MHz
`synthesis/sky130_vex2_soc/config_5mhz.yaml` (CLOCK_PERIOD 200, otherwise identical: same 2000 x 2000 um die, same two SRAM22
blocks, `sky130_fd_sc_ms`), run tag `sky130_vex2_soc_5m`, 15 min. Setup slack +155.8 ns (critical path 44.2 ns), hold +0.100 ns,
0 DRC errors, 63,890 standard cells / 0.3672 mm2 (50 MHz: 63,774 / 0.3671 mm2, 1,929 hold buffers; 5 MHz: 1,933). The SoC cell
count is unchanged because its cells were already minimum-size at 50 MHz; the die is not resized (macro pin access), so its
utilization stays at 13 % of the non-macro core area (documented reason: two 674 x 782 um macros with fixed pin sides).

## E11. SRAM22 per-access figures (from the liberty `sram22_2048x32m8w8_tt_025C_1v80.lib`)
Internal power is characterized on the clock pin only, per state (values in pJ per edge, C*V^2 units of the liberty):
read (`!we&ce`): rise 14.32 (vdd table) + 14.65 (vss table), fall 0.72 + 0.27; write (`we&ce`): rise 9.32 + 9.76, fall 0.73 + 0.28;
idle clocked (`!we&!ce`): rise 0.52 + 0.97, fall 0.64 + 0.16; leakage 2,336.8 nW = 2.34 uW (state-independent to 0.04 %). The liberty
carries the same energy once for the power pin and once for the ground pin; OpenSTA 2.6.0 sums every internal_power group
regardless of `related_pg_pin` (power/Power.cc, findInputInternalPower), so its macro power is twice the supply energy. Check on the
50 MHz 500-bin window of `bmi_snn_top` (92,411 cycles, 55,489 reads = 16 x (2,934 + 500) + 545 spikes): vdd-only energy 55,489 x
15.04 pJ + 36,922 idle edges x 1.16 pJ = 877 nJ -> 474 uW; summing both rails gives 1,747 nJ -> 945 uW, which is the 8.7 % block
share ("about 950 uW") of Table 8. Per bin (111 reads): 1.75 nJ from the supply (about 15 pJ per 32-bit read), 3.5 nJ as reported by
OpenSTA. Consequence: the SRAM-core energies of the 50 MHz tables overstate the block by about 1.75 nJ per bin (4 % of 40 nJ); the
5 MHz power runs of the SRAM cores use a power-only copy of the liberty (vss groups removed) and the as-generated result is kept as
a sensitivity figure. Published comparison: to be added (E11 text).

## Method note: streamed toggle counts (E4, E7)
`tools/vcd_toggles` (sim/vcd_toggles.c) reads the VCD from a FIFO while the simulator writes it and accumulates per-pin transition
counts and high times with OpenSTA's rules (initial value not counted, x/z transitions 0.5); `power/toggles_to_activity.py` emits
`set_power_activity -pins/-input_ports -activity -duty` for every cell pin and input port, and `power/run_toggles_power.sh` runs
OpenSTA once. Validation on the 500-bin functional window of `bmi_snn_sp` (50 MHz netlist): 7.040499 mW against 7.040497 mW with
`read_power_activities -vcd` on the stored waveform (all groups agree to 6 digits); 80,323 pins and 110 input ports annotated in both.
Full test blocks therefore run without storing waveforms (`sim/run_gls_stream.sh`, `sim/measure_full.sh`); per-bin minima and
maxima come from the testbench's per-bin cycle statistics.

## Method finding (round 5): the root clock network is not annotated by OpenSTA
Observed on the front end (E10): the v2 design switches its 5 MHz oscillator on for 3.05 % of the time (305,075 of 10.0 M
oscillator cycles in the 500-bin, 2.0 s simulation), yet `read_power_activities -vcd` returned the same clock-tree power as the
free-running v1 (3.71 vs 3.70 uW; total 4.85 vs 4.83 uW). Tests (all on OpenSTA 2.6.0 of the OpenLane 2.3.10 environment; the
OpenROAD build of OpenROAD-flow-scripts rev b4dbcb4 behaves the same): (1) the per-pin `set_power_activity -pins` path
(`power/run_toggles_power.sh`) with the measured activity on every clock pin gives the identical result; (2) on the 50 MHz
`bmi_snn_sp` waveform (root clock running, three clock gates, 1,490 gated flip-flops, 652 gated clock buffers) the per-instance
power was compared with a run whose data activities are all zero (`GLOBAL_ZERO=1`, clock-driven power at the full rate): the gated
clock buffers draw 0.41 of their full-rate power for a measured 0.39 activity ratio, the gated flip-flops 0.53 (clock share plus
data), the root buffers 1.00 (activity 2.0 per cycle in the waveform as well). So OpenSTA takes the activity of the pins between
the clock port and the first clock-gate cell from the clock definition and ignores the annotation there, while everything
downstream of a clock gate follows the annotated activity. The gated cores of all rounds are therefore measured correctly; only a
root clock that is stopped in the waveform is over-counted. `set_clock_sense -stop_propagation` at the port is not a fix (the
combinational power of the domain drops to zero, 7.04 -> 3.70 mW on `bmi_snn_sp`, because activities are converted with the clock
that reaches each pin); stopping at the clock-gate outputs changes nothing (7.040497 mW both). Power runs without any
`create_clock` are meaningless (1e23 W).
Correction used for the front end (`power/root_clock_correction.py`): walk the root network of `clk5` in the routed netlist (4 clock
buffers, the clock gate's clock pin, 5 flip-flops clocked directly by `clk5`), take their clock-driven dynamic power from the
zero-data run (`power/out_vcd_fe_5m_gls_clk5only`, for the buffers equal to the annotated run) and keep the fraction given by the
oscillator duty: P = P_annotated - (1 - 0.0305) x P_clock-driven. Result: 0.691 uW instead of 4.85 uW (Sequential 0.345, Clock
0.321, Combinational 0.025, leakage 0.014 uW; 4.16 uW removed, 91 % of it in the three root clock buffers). The gated core clock
(`core_clk`, 46 cycles per bin) and the 32.768 kHz domain need no correction (annotated, respectively running throughout).

## E10. Digital front end (`rtl/bmi_fe.v`)
Two clock domains: a 32.768 kHz always-on domain (131 cycles = 3.998 ms per bin: 96-bit activity register `act`, snapshot `snap`,
bin counter, oscillator enable) and a 5 MHz domain that only runs while the oscillator is enabled (event serializer with a two-level
first-set search over the 96-bit snapshot, tick, wait for the core's `bin_done`, then `osc_en` low). The core clock is gated by a
`sky130_fd_sc_hd__dlclkp_4` (open during reset so that the fast-domain flops initialize). v1 (`rtl/bmi_fe_v1_freerunning.v`) kept
the 5 MHz clock running: 4.83 uW, 3.70 uW of it in the clock tree; the redesign with the oscillator enable is the design lesson
recorded for the paper. Testbench `sim/tb_bmi_fe.v`: recorded stream of indy_20160630_01 replayed as spike pulses at random
positions inside the 32 kHz cycles, behavioural core with random `ev_ready` stalls, per-bin set comparison; 500 bins pass at RTL and
on the netlist (`sim/run_fe.sh rtl|gls 500 --vcd`). Hardening (`synthesis/bmi_fe/config.yaml`, `bmi_fe.sdc` with the second clock and
`set_clock_groups -asynchronous`): utilization policy accepted at 60 % (tag `bmi_fe_5m_u60`, 6 min): 2,328 cells, 0.0200 mm2,
setup +57.8 ns, hold +0.307 ns, 0 DRC. Gate-level 500 bins: 305,332 clk5 cycles (611 per bin, 122 us of oscillator time per bin),
22,858 gated core clock cycles (46 per bin), 65,500 slow cycles, all 2,934 events serialized once. Power at 250 bins/s (the
simulation runs in real time): 0.691 uW after the root-clock correction (4.85 uW as reported by OpenSTA; see the method note),
of which 0.158 uW in the 32.768 kHz clock tree, 0.096 uW in the 5 MHz clock tree at 3 % duty, 0.345 uW in the flip-flops (mostly
the 96-bit activity and snapshot registers at 32.768 kHz) and 0.014 uW leakage; `paper/numbers_frontend.tex` by `sw/collect_frontend.py`.

## E7. SoC per-pin method (decoding window)
`sim/measure_soc_window.sh <vcd> <run> <period_ns> <tag>`: `sw/riscv_window.py` finds the decoding window (last `wake` before
`gpio_done` to `gpio_done`; 144,488 cycles = 9,030.5 per bin for -O2, 76,726 = 4,795.4 for the tuned firmware, 16 bins),
`tools/vcd_toggles --begin --end` accumulates the toggles of that window only, `power/run_toggles_power.sh riscv` annotates them.
The SoC waveform is a level-1 dump (nets of the flat netlist, 17,709 variables, 2,050 of them buses), so the converter annotates
each net's driver pin (`__net_act`), as `read_power_activities -vcd` does; bus bits are carried as a separate column of the toggle
file so that escaped bus names (`\u_cpu.x[9]`) resolve. The first pass without the net mode annotated 3 input ports only (OpenSTA
then propagated estimated activities: 10.5 mW) and is discarded. Both SRAM liberty conventions are run (vdd-only copy `_pwr.lib`
as the primary figure, as-generated as sensitivity). Results: see the E7 table below.

## E11 (continued). Published comparison
Cosemans, Dehaene and Catthoor, "A 3.6 pJ/access 480 MHz, 128 kb on-chip SRAM with 850 MHz boost mode in 90 nm CMOS with tunable
sense amplifiers", IEEE J. Solid-State Circuits 44(7), 2009: 3.6 pJ per 32-bit access in 90 nm at 1.2 V (a low-energy design point);
the SRAM22 figure of about 15 pJ per 32-bit read at 1.8 V in 130 nm is 4x higher, consistent with the technology and supply
(energy scales with C V^2: (1.8/1.2)^2 = 2.25x from the supply alone) and with a compiler-generated, uncharacterized-for-energy
macro. The paper text quotes the SRAM22 per-access figure and this reference point; the OpenSTA double counting is stated as the
reason for the 2x between the 50 MHz tables and the corrected 5 MHz figures.

### E7 table: SoC per-pin power over the decoding window, 50 MHz (existing waveforms), 16 bins

| firmware | SRAM liberty | P window (mW) | E per bin (nJ) | macro (uW) | clock (mW) | sequential (mW) | combinational (mW) | leakage (uW) |
|---|---|---|---|---|---|---|---|---|
| -O2 (released) | pwr | 19.583 | 3,537 | 222.3 | 5.642 | 5.215 | 8.504 | 4.67 |
| -O2 (released) | asgen | 19.799 | 3,576 | 437.9 | 5.642 | 5.215 | 8.504 | 4.67 |
| -O3 hand-tuned | pwr | 21.011 | 2,015 | 252.1 | 5.647 | 5.225 | 9.887 | 4.67 |
| -O3 hand-tuned | asgen | 21.256 | 2,039 | 497.2 | 5.647 | 5.225 | 9.887 | 4.67 |

Window: -O2 144,488 cycles (9,030.5 per bin), tuned 76,726 (4,795.4 per bin); the SoC is awake for the whole window (144,485 and
76,723 awake cycles), so the clock definition and the annotated root clock coincide. Reference-flow figures of the previous rounds
(P_awake x cycles x 20 ns): 2,561 nJ per bin (-O2); the per-pin method gives 38 % more because the reference flow's awake power
was an OpenSTA estimate with propagated activities. The 5 MHz waveforms (sim/build_riscv_gls_5m*, dumps running) are
processed the same way when they finish.

## E1 (continued). Policy attempts aborted, watchdog added (2026-09-19, 16:00)
The 60 % attempts of the larger cores did not converge in detailed routing and were still running after 7-8 h with tens of
thousands of violations (bmi_snn_min32 100,462 after 3 iterations, bmi_snn_ming 286,322 after 1, bmi_snn_sp_s622 121,897 after 4,
bmi_snn_g32p50 58,769 after 3, GF180 bmi_snn_min16 40,924 after 4; bmi_snn_lmin2 had not completed one iteration in 3 h; the
bmi_snn_sp 50 % attempt stood at 4,872 violations after 4 iterations without progress for 8 h; the bmi_snn_m12 40 % attempt
stalled after "GRT-0097 no global routing found"). These attempts were killed and logged as rejected (logs/policy_round5.log,
DRT logs kept in logs/policy_round5_killed/). `synthesis/harden_policy2.sh` adds a watchdog to the policy: an attempt is aborted
when detailed routing has more than 20,000 violations after 3 iterations, more than 3,000 after 8, or no completed iteration for
3 h. The remaining utilization lists continue the policy from the last rejected step (sp, m12: 40 30 20; min32: 50 40 30; ming:
40 30 20; lmin2, lmem2: 30 20 since their 50 MHz hardenings needed 22-25 %; min, hw: 60 50 40 30; grid variants: 50 40 30 given
the g32p50 result at 60 %; per-session netlists as their main cores). Accepted so far: min16 60 %, fe 60 %, top 60 % (die 920 x
900 um, 64 min), topg 40 % (die 1170 x 900 um), g16p50 60 % (138 min), GF180 sp 50 % (73 min), GF180 m12 30 %, GF180 min32 40 %;
ORFS: NanGate45 sp 60 / m12 40 / min32 60 / min16 60, ASAP7 RVT sp 60 / m12 50 / min32 60 / min16 60, ASAP7 SRAM-Vt sp 60 /
m12 50 / min32 60 / min16 60; lmin2 fails at synthesis on the ORFS kits (no latch mapping configured for NanGate45/ASAP7, rc=2 in
under a minute at every utilization) and is reported for sky130 and GF180 only. IHP sp at 60 %: 65,116 violations after 7 h,
aborted, driver continues at 50 %.

## E4 (continued). Session policy of the full blocks
A hardwired core carries the weights of one session (indy_20160630_01 for the main cores), so a full block of another session
through it is a wrong-weights run: the first min16 run of indy_20160622_01 (132,745 bins, 7.2 h) reported 132,745 mismatches
against the session's own reference and is discarded (kept under sim/_invalid_wrong_weights/). Policy: hardwired cores -> full
block of indy_20160630_01; per-session netlists (E3, *_s622/*_s131) -> full block of their own session; programmable cores
(top, topg, lmem2, lmin2, ...) -> full block of indy_20160630_01 and 20,000 bins of each other session with that session's
weights loaded. `sim/pipeline5.sh` implements this; `sw/collect_designs5.py` reads the same layout.

### E7 (continued): 5 MHz waveforms, firmware mix-up, idle power
The two 5 MHz gate-level runs launched in parallel at 07:36 both picked up the hand-tuned firmware image (`sim/run_riscv.sh`
rebuilds `firmware/` in place and the two concurrent builds copied the same binary: identical `imem.hex`, identical decoding
window of 76,726 cycles). The tuned 5 MHz result stands (`power/out_soc_tuned_5m`: 2.089 mW over the window, 2,003 nJ per bin
with the vdd-only SRAM liberty, 2,027 nJ as generated); the -O2 run was repeated with a clean firmware build (`make clean`,
`FW_OPT=-O2 FW_SRC=bmi_snn_sw.c`, started 16:00, `imem.hex` identical to the 50 MHz -O2 run). Idle power with the clock running
(8,000 cycles of the sleep phase before the decoding wake, `sram_clk_en` low): 76.0 uW at 50 MHz (leakage 4.67 uW), i.e. the
per-pin method gives a much lower idle figure than the reference flow's 440 uW (propagated activities). Per-pin idle at 5 MHz
follows from the -O2 run. `sw/collect_software5.py` -> results/explore/software5.json, paper/numbers_software5.tex.

## Figures and paper build (2026-09-19, 16:15)
F4: `paper/main.tex` now inputs `figures/arch-improved.tikz`; the weights block of panel (b) names the three sources (register
file, latch memory, hardwired constants); caption shortened to four lines (what (a) and (b) are, the shared panel, where the
per-bin work is listed). F5: `sw/fig_accuracy.py` legend gives each baseline its architecture and window (from the NeuroBench
scripts examples/primate_reaching/{ANN.py, SNN2.py, SNN_3.py, benchmark_*.py}: ANNModel2D = 96-32-48-2 fully connected, ReLU,
batch norm, dropout 0.5, on the spike counts of a 200 ms window, "2D" = [batch, channels] input against the 3D variant with 7
time steps; SNNModel3 = three snntorch Leaky layers 96-32-48-2, 200 ms window in 7 steps; SNN2 = Leaky 96-50-2, tau 0.96,
streamed per 4 ms bin) and prints the R2 above every bar of this work. F6: `energy_bars_energy.pdf` (energy panel only) replaces
the three-panel figure; latency and average power stay in the table. F1 (`figures/fig_pareto.py`), F2
(`figures/fig_pavg_vs_rate.py`), F3 (`figures/fig_power_breakdown5.py`) are generated from results/pareto.csv, results/pdks5.json
and results/designs.json and are re-run as the measurements arrive (F3's 37 C leakage: exponential interpolation between the
25 C and 100 C typical liberties of the idle run, e.g. min16 0.064 uW at 25 C, 9.03 uW at 100 C -> 0.14 uW at 37 C).
`paper/numbers_pdks.tex` keeps the macro names of the previous rounds for the min16 rows (plus `Low`/`Mid` for the GF180 supply
variants) and adds `<Kit><Core>` macros; the paper compiles with tectonic after the regeneration (placeholders `--` where a kit has
no result yet).

## E5 (continued). GF180 latch-memory core
The retargeted `rtl/gen/pdk/*/bmi_snn_lmin2.v` still instantiated the 161 sky130 row clock gates of the latch memory
(`sky130_fd_sc_hd__dlclkp_1`): the generator replaced only the top-level clock gates. Replaced by the kit's cell
(`gf180mcu_fd_sc_mcu7t5v0__icgtp_1`, `sg13g2_lgcp_1`, `CLKGATETST_X1`, `ICGx1_ASAP7_75t_R/_SRAM`) and the GF180 policy run
restarted at 30 %; the ORFS kits' lmin2 synthesis failures (rc=2 in under a minute) had the same cause and can be retried if time
allows (`synthesis/run_orfs5.sh <plat> bmi_snn_lmin2 rvt "30 20"`).

## E12. Bootstrap confidence intervals on R2 (`sw/bootstrap_r2.py`)
Moving-block bootstrap over the test block of each session (block 250 bins = 1 s, 1,000 resamples) of the integer-reference
prediction of the released H=64 model: 95 % intervals indy_20160622_01 [0.617, 0.664], indy_20160630_01 [0.506, 0.568],
indy_20170131_02 [0.530, 0.606]; mean over the three sessions [0.564, 0.600] (point estimate 0.5825). `paper/numbers_bootstrap.tex`,
results/explore/bootstrap.json.

## E5 (continued). Annotated simulation of the GF180 and ASAP7 netlists under Icarus (2026-09-19, 17:00)
The first annotated runs of both kits did not complete a single bin (ASAP7: 7 h, GF180: 3 h timeout), also with two-bin tests.
Causes and fixes, each verified with a two-bin bit-exact run of the 5 MHz `bmi_snn_min16` (GF180) and `bmi_snn_sp` (ASAP7):
- GF180: with the vendor model files compiled before the testbench (the order of `sim/run_gls_stream.sh`), the clock buffers'
  outputs resolve to X under `-gspecify` (the netlist and `primitives.v` carry no `timescale directive and inherit Icarus's default
  time unit; module path delays then never propagate); with a `timescale 1ns/1ps` file compiled first (`sim/timescale_1ns_1ps.v`)
  the same netlist passes. The vendor timing bodies are used with the `notifier` regs initialized to 0
  (`/media/pdk/icarus_sdf_models/gf180mcu_fd_sc_mcu7t5v0_sdf.v`; Icarus has no timing checks, an uninitialized notifier drives the
  flip-flop UDPs to X). Icarus drops the edge-sensitive `ifnone` paths of the xor2/xnor2 cells ("sorry: ifnone with an
  edge-sensitive path is not supported"): 2,144 of 80,989 IOPATH entries of `bmi_snn_min16` stay unannotated (those cells keep zero
  delay), all flip-flop, clock-gate and other combinational paths are annotated. A first pass with `-DFUNCTIONAL` (functional
  wrappers) annotated nothing (glitch factor 1.0007) and was discarded.
- ASAP7: the vendor SEQ models (`altos_dff` UDPs with `notifier`, clocked from the `delayed_*` nets of `$setuphold`) stay X
  under Icarus; `sim/asap7_seq_icarus.v` provides behavioural DFFHQNx1/2/3, ICGx1 and DHLx1 (RVT and SRAM-Vt names) with the same
  IOPATH paths, the vendor AO/INVBUF/OA/SIMPLE models are kept. The OpenSTA SDF (`write_sdf`, liberty time unit ps, header
  `(TIMESCALE 1ps)`) is read by Icarus in the module time unit (ns), which turns 113 ps flip-flop delays into 113 ns and stalls the
  core: `sim/sdf_sanitize_for_icarus.py` now rescales any non-ns SDF to ns and fills the empty rise triplets of the conditional
  ICG paths with zeros. Two bins of `bmi_snn_sp` on ASAP7 RVT then pass bit-exact with all 47,117 INTERCONNECT and all IOPATH
  entries matched.
The 200-bin annotated windows of sp, m12, min32 and min16 on GF180, ASAP7 RVT and ASAP7 SRAM-Vt are queued with these fixes
(`sim/pdk5_queue.sh ... :sdf`).

## E14 (continued). Timing-driven placement crash with the 1.28 V corner
`bmi_snn_sp_5m_lv` (40 %, ss_n40C_1v28 as DEFAULT_CORNER) died in OpenROAD's timing-driven global placement at "Timing-driven:
executing resizer for reweighting nets" (silent exit after 26 min, "OpenROAD.GlobalPlacement failed unexpectedly"). The run is
repeated with `PL_TIMING_DRIVEN: false` (wire-length-driven placement; the later repair steps still use the 1.28 V corner), which
is recorded in `config_lowv.yaml`; the same setting applies to m12 and min32.

## E8. One state width for every core (optional)
Not run in this round: the 12/14-bit variants of `bmi_snn_top` and `bmi_snn_lmem2` would each need a new generated RTL, a policy
hardening of a 400k-instance latch design and the full measurement set; the budget went to E1-E5 and E9. The 12-bit gated
hardwired cores (m12, sp, the E2 grid) and the 12-bit latch core (lmin2) already cover the state-width comparison for the
parallel architecture; the sequential SRAM core keeps 20/24 bits.

### E5 interim results (17:35): ASAP7 annotated and low-voltage rows
ASAP7 RVT / SRAM-Vt at 5 MHz, 60 % (m12: 50 %), 200 annotated bins bit-exact, all SDF paths matched: glitch factors sp 1.074 /
1.075, m12 1.101 / 1.107, min32 1.076 / 1.076, min16 1.071 / 1.071 (RVT / SRAM-Vt). The SS liberty of ASAP7 is characterized at
0.63 V and 100 C: the total energy per bin at that corner (RVT sp 0.175 nJ against 0.058 nJ at TT) is dominated by the 100 C
leakage (46.5 uW against 3.3 uW at 25 C) over the 4.2 us of a decode; the dynamic part falls to 0.038 nJ (-35 %). f_max at the SS
corner from the worst setup slack at 200 ns: 2.3 GHz (RVT sp), 1.8 GHz (SRAM-Vt sp). GF180 supplies (typical liberties, 25 C):
sp 23.8 nJ at 5 V, 9.56 nJ at 3.3 V, 2.60 nJ at 1.8 V (f_max 82 MHz), 2.10 nJ at the ss 1.62 V 125 C corner (f_max 33 MHz).
`results/PDKS5.md` carries the full table; the paper table `pdks_table.tex` lists the dynamic part next to the total at the low
supply and the corner temperature.

## E2. Training grid (integer-reference R2, 5 seeds x 3 sessions; `sw/run_grid_round5.sh`, `sw/eval_int.py`, `sw/collect_pareto.py`)
90 trainings (H = 128 dense / 25 % / 12.5 %, H = 32 50 % / 25 %, H = 16 50 %; seeds 0-4; three sessions) finished at 11:54 after 5 h;
the H = 64 seed models of the previous rounds were re-evaluated with the integer reference so that every row of the grid uses the same
metric. Mean over sessions, sd over seeds:

| H | synapses | seeds | R2 int mean +- sd | min-max | seed-0 R2 on indy_20160630_01 | hardened core |
|---|---|---|---|---|---|---|
| 128 | 100 % | 5 | 0.586 +- 0.00335 | 0.582-0.59 | 0.542 | bmi_snn_g128 |
| 128 | 25 % | 5 | 0.572 +- 0.00483 | 0.566-0.579 | 0.545 | bmi_snn_g128p25 |
| 128 | 12.5 % | 5 | 0.546 +- 0.00341 | 0.542-0.551 | 0.525 | bmi_snn_g128p125 |
| 64 | 100 % | 5 | 0.581 +- 0.00271 | 0.578-0.585 | 0.537 | bmi_snn_m12 |
| 64 | 50 % | 4 | 0.579 +- 0.00138 | 0.577-0.581 |  | bmi_snn_g64p50 |
| 64 | 25 % | 4 | 0.572 +- 0.00142 | 0.57-0.573 |  | bmi_snn_sp |
| 64 | 12.5 % | 4 | 0.527 +- 0.00722 | 0.517-0.533 |  | bmi_snn_g64p125 |
| 32 | 100 % | 5 | 0.574 +- 0.00359 | 0.571-0.58 | 0.517 | bmi_snn_min32 |
| 32 | 50 % | 5 | 0.573 +- 0.00372 | 0.569-0.578 | 0.515 | bmi_snn_g32p50 |
| 32 | 25 % | 5 | 0.556 +- 0.00362 | 0.55-0.561 | 0.514 | bmi_snn_g32p25 |
| 16 | 100 % | 5 | 0.552 +- 0.00458 | 0.546-0.556 | 0.499 | bmi_snn_min16 |
| 16 | 50 % | 5 | 0.544 +- 0.0041 | 0.539-0.549 | 0.492 | bmi_snn_g16p50 |

The 128-neuron dense network gains 0.005 over H = 64 dense (0.586 against 0.581) and the 25 % pruned H = 128 matches the dense H = 64;
H = 32 dense (0.574) sits above the 0.55 threshold with all seeds, H = 16 dense (0.552) and H = 16 50 % (0.544) straddle it. The hardware
columns of `results/pareto.csv` (energy, area, P_avg of the 12-bit gated hardwired core of each seed-0 model) fill in as the E2 hardenings
(`bmi_snn_g*`, queue q5) and their measurements complete; figure F1 (`figures/fig_pareto.py`) is regenerated from the same file.

### E5 interim results (17:55): GF180 annotated rows and sky130 low-voltage rows
GF180 (5 V, 200 annotated bins bit-exact, vendor timing bodies): glitch factors sp 1.078, m12 1.112, min32 1.067, min16 1.060
(sky130 at 5 MHz: sp 1.18, min32 1.21, min16 1.22; ASAP7 1.07-1.11). sky130 5 MHz netlists re-evaluated with ss_n40C_1v28 on their
500-bin waveforms: sp E 1.126 nJ (dynamic 1.126), leakage 0.0867 uW at -40 C, setup slack 142.9 ns, f_max 17.5 MHz; min32 E 1.448 nJ (dynamic 1.448), leakage 0.0487 uW at -40 C, setup slack 145.2 ns, f_max 18.2 MHz; min16 E 0.687 nJ (dynamic 0.687), leakage 0.0184 uW at -40 C, setup slack 157.0 ns, f_max 23.3 MHz.
Note on f_max: the low-voltage slacks come from OpenSTA on the routed netlist with its SPEF and a propagated clock but without the
flow's input/output delay constraints (OpenLane: 20 % of the period), so they are not the signoff slacks of the hardening (sky130
sp: 142.9 ns at 1.28 V against a signoff slack of 118 ns at 1.8 V that includes 40 ns of IO delay); f_max = 1 / (200 ns - slack)
is the register-to-register bound at that corner and is computed the same way for every kit.

## E5 (continued). Latch-memory core on the ORFS kits: out of memory
`bmi_snn_lmin2` (400k instances) on ASAP7 RVT at 30 %: detailed routing was killed by the kernel (signal 9) at a peak of 19 GB
after 77 min while the sky130 policy runs, the full-block simulations and the OpenSTA power runs (up to 11 GB each) shared the
62 GB of the machine; the 20 % attempt follows. The GF180 lmin2 attempts that ended silently after 5 min during global placement
had the same signature. The ORFS lmin2 rows stay optional in E5 ("attempt"); the sky130 and GF180 lmin2 hardenings run with the
watchdog and are the ones reported.

### E14 result: bmi_snn_sp hardened at 1.28 V (18:20)
`bmi_snn_sp_5m_lv` (40 %, ss_n40C_1v28 as default corner, wire-length-driven placement): DRC-clean, timing met at all twelve
corners (setup +113.0 ns and hold +2.05 ns at nom_ss_n40C_1v28; worst hold over the corner set +0.024 ns at the fast corner),
32,484 cells / 0.2023 mm2 against 24,546 cells / 0.1761 mm2 for the TT-signoff netlist at the same utilization: the slow-corner
signoff costs 32 % more cells (hold buffers and upsizing for the 1.28 V paths). Its annotated 200-bin run at the 1.28 V corner
(`sim/measure_lowv.sh`) runs next; m12 and min32 follow when their 5 MHz TT hardenings are accepted.

### E7 final table (per-pin OpenSTA power over the decoding window, vdd-only SRAM liberty; as-generated liberty in brackets)

| firmware | clock | cycles/bin | latency ms | P window mW | E per bin nJ | idle uW (clock on, asleep) | leakage uW | P_avg 250 bins/s uW: clock stopped / running / 32.768 kHz |
|---|---|---|---|---|---|---|---|---|
| o2 | 50 MHz | 9030.5 | 0.181 | 19.583 | 3,537 (3,576) | 76.0 | 4.67 | 889 / 960 / 889 |
| tuned | 50 MHz | 4795.4 | 0.096 | 21.011 | 2,015 (2,039) | 76.0 | 4.67 | 508 / 580 / 508 |
| o2 | 5 MHz | 9021.5 | 1.804 | 1.952 | 3,522 (3,561) | 11.9 | 4.67 | 885 / 892 / 885 |
| tuned | 5 MHz | 4795.4 | 0.959 | 2.089 | 2,003 (2,027) | 11.9 | 4.67 | 505 / 513 / 506 |

The energy per bin is the same at 5 MHz and 50 MHz to within 0.4 % (-O2: 3,522 against 3,537 nJ; tuned: 2,003 against 2,015 nJ):
the SoC's decode is a fixed number of cycles and its leakage over a 1.8 ms decode is 8 nJ. The clock frequency only matters for the
idle power with the clock running (76 uW at 50 MHz, 11.9 uW at 5 MHz). Per-pin against the reference flow of the previous rounds:
-O2 3,537 nJ against 2,561 nJ (ratio 1.38); the reference flow's awake power came from OpenSTA's propagated activities, so the
software ratios of the paper move from bounds to measurements (macros in `paper/numbers_software5.tex`: `\eCpuOtwoFive`, `\ratioCpuOtwoFiveSp`, ...).

### E4 first full block (18:55): bmi_snn_g16p50
Full test block of indy_20160630_01 (107,444 bins, 524,200 events = 4.88 per bin, streamed toggles, 2 h 53 min): 0.822 nJ per bin
zero-delay against 0.93 nJ on the 500-bin window (5.87 events per bin), per-bin range 0.245-3.23 nJ (sd 0.357); 5,000 annotated
bins: 0.973 nJ against 1.10 nJ on the 200-bin window. Both runs bit-exact. The remaining cores follow the same path as their
hardenings and windows complete (`sim/pipeline5.sh`); the per-session and full-block macros (`\eFull<Sh>B`, `\eSdfW<Sh>B`,
`\eFullMin/Max<Sh>B`, `\evFull<Sh>B`) are in `paper/numbers2.tex`.

### E14 measurement (19:00): bmi_snn_sp hardened at 1.28 V
Annotated 200-bin run with the nom_ss_n40C_1v28 SDF and the 1.28 V liberty (bit-exact): 1.43 nJ per bin against 3.15 nJ for the
TT-signoff netlist at 1.8 V (2.2x), leakage 0.0732 uW at -40 C by liberty definition, average power at 250 bins/s 0.431 uW
(clock stopped). The TT-signoff netlist re-evaluated at 1.28 V with its own activity gives 1.13 nJ on the zero-delay window
(`sky130/sp` row of E5) - fewer cells than the 1.28 V hardening, which carries 32 % more cells for the slow-corner timing; the
hardened figure is the one that is timing-safe at 1.28 V (setup +113 ns, hold +2.05 ns at that corner). Macros
`\cnrFive...Sp` in `paper/numbers_corners5.tex`, table `paper/corners_table5.tex`.
Addendum: on the annotated 200-bin window the TT-signoff netlist re-evaluated at 1.28 V gives 1.34 nJ per bin (setup slack 142.9 ns,
f_max 17.5 MHz without IO constraints), i.e. the hardened 1.28 V core (1.43 nJ) costs 7 % more than the liberty swap for its
timing safety at the slow corner.

### E1 (continued): stalled detailed-routing starts (20:00)
`bmi_snn_m12` at 40 % (and, earlier, `bmi_snn_sp` at 50 %) entered detailed routing and never wrote a routing iteration: the DRT
log stopped one minute after the step started and stayed silent for 3 h (m12) and 8 h (sp) while the process kept consuming CPU
(pin-access analysis or initial routing at that density). The watchdog's idle rule (no completed iteration for 3 h) ends such
attempts; it now counts from the start of detailed routing rather than from the start of the flow. `bmi_snn_min` at 60 %
(290,447 violations after its first iteration) was stopped by hand ahead of the watchdog. Both cores continue at the next lower
utilization (m12 30 %, min 50 %).

### E4 scheduling (20:15)
The SRAM core simulates about 35 bins per minute at gate level (185 cycles per bin and the behavioural SRAM model), so its full
block of indy_20160630_01 takes about two days; the six E4 windows of `bmi_snn_top` and `bmi_snn_topg` (full block of B, 20,000
bins of A and C, 2,000 annotated bins per session as E4 allows for the SRAM core) therefore run in parallel instead of in the
sequential pipeline (`sim/topg_windows.sh`, and the same commands by hand for top). The latch and register-file memory cores
(lmin2, lmem2, lmem, scmem) get 5,000-bin windows per session (E4 asks for at least 5,000 bins for these), the hardwired cores
their full own-session block.

### E1 (continued): hold at the fast corner for the 12-bit gated cores (21:20)
`bmi_snn_m12` at 30 % routed DRC-clean and met setup at every corner (+118 ns) but failed hold by 0.139 ns on 5 endpoints at
max_ff_n40C_1v95 (the nested clock gates of this core; the 50 MHz hardening needed a 0.5 ns hold margin for the same reason).
Since a lower utilization does not address hold, the policy's 20 % step was stopped and the 30 % run is repeated with the
hold-repair margin raised from 0.5 to 0.8 ns (`EXTRA_YAML` amendment of `synthesis/harden_policy2.sh`, run tag suffix `h`); the
per-session `bmi_snn_m12_s131` starts directly at 30 % with the same margin (its 40 % attempt would stall in routing like m12
and m12_s622), `bmi_snn_m12_s622` at 30 % is still running with the original margin and is repeated the same way if it fails hold.

### E4 / E3 results (21:45): min16 full block, sp_s131 own-session block
`bmi_snn_min16` (5 MHz, 60 %): full block of indy_20160630_01, 107,444 bins bit-exact, 1.498 nJ per bin (4.88 events per bin)
against 1.687 nJ on the 500-bin window (5.87 events per bin, +13 %); 5,000 annotated bins 1.833 nJ against 2.062 nJ on the 200-bin
window; per-bin energy 0.444-5.78 nJ. `bmi_snn_sp_s131` (weights of indy_20170131_02, 40 %): full block of its own session,
52,116 bins bit-exact, 1.774 nJ per bin (3.71 events per bin; window 1.753 nJ); 5,000 annotated bins 2.044 nJ; per-bin range
0.594-22.7 nJ (one burst bin). The 50 MHz transfer model of the previous rounds predicted 2.31 nJ for this session at its
whole-session mean rate (3.95 events per bin) with the indy_20160630_01 weights; the per-session netlist at 5 MHz needs 23 % less.

### E14 (continued): bmi_snn_min32 at 1.28 V (22:45)
At the TT utilization (50 %) the 1.28 V hardening did not route: 58,294 -> 53,634 -> 51,203 -> 45,169 violations over four
detailed-routing iterations (5.5 h), against a DRC-clean TT run at the same utilization; the hold and setup repair for the slow
corner adds cells and wire. Stopped and repeated at 40 % (`LV_UTIL=40` in `synthesis/harden_lowv.sh`, i.e. the E1 policy step
applied to the low-voltage signoff). `bmi_snn_m12` at 1.28 V waits for its TT acceptance.

### E5 (continued): GF180 latch-memory core at 30 % (22:50)
`pdk_gf180/bmi_snn_lmin2` at 30 % (206,902 cells, 5.08 mm2) routed DRC-clean after 6.6 h and met setup at every corner but failed
hold by 0.127 ns on 3 endpoints at max_ff_n40C_5v50, like the sky130 m12 at its fast corner. The policy's 20 % step was stopped
(hold is not a utilization problem) and the 30 % run is repeated with the hold-repair margin raised to 0.8 ns (tag
`bmi_snn_lmin2_5m_u30h`); its annotated measurement follows E9's 50-bin rule on GF180 as well if time allows.

### E3 (continued): per-session H=32 netlists (22:55)
The configurations of `bmi_snn_min32_s622` and `bmi_snn_min32_s131` referenced the constraint file of `bmi_snn_min32` without a copy
in their directories, so their first attempts failed at configuration load within minutes (removed from the policy log); the file is
copied and the two policies restart at 50 %. `bmi_snn_m12_s131` was accepted at 30 % with the 0.8 ns hold margin (90 min).

### E1 (continued): bmi_snn_m12 accepted (23:10)
`bmi_snn_m12` at 30 % with the 0.8 ns hold margin: DRC-clean, timing met at all corners (105 min, tag `bmi_snn_m12_5m_u30h`);
its 500/200-bin windows, full block and 5,000 annotated bins start (`sim/pipeline5.sh`), and the 1.28 V hardening (E14) at the
same utilization is launched (a stale waiter still carrying the wrong OpenLane key had to be replaced).

### E3 (continued): bmi_snn_m12_s622 (00:15, 20 Sep)
The 30 % attempt with the original hold margin stalled at the start of detailed routing (no iteration in 3 h, 240 min in total) and
was ended by the watchdog; it is repeated at 30 % with the 0.8 ns hold margin used for m12 and m12_s131 (both converged at 30 %
with it), 20 % as the fallback step.

### E3 (continued): bmi_snn_m12_s622 (00:55, 20 Sep)
The original policy instance had survived the queue kill and, after its stalled 30 % attempt, converged at 20 % with the original
hold margin (40 min, DRC-clean, timing met): the policy's own answer for this core. The 30 % rerun with the 0.8 ns hold margin
(as accepted for m12 and m12_s131) runs in parallel; if it converges it replaces the 20 % netlist for a like-for-like comparison
of the three per-session m12 netlists, otherwise the 20 % result stands. The measurement pipeline started on the 20 % netlist.

### E4 results (02:45, 20 Sep): sp, g32p50, g32p25 full blocks
Full test block of indy_20160630_01 (107,444 bins, 4.88 events per bin, all bit-exact): `bmi_snn_sp` 2.365 nJ per bin (500-bin
window 2.674 nJ, +13 %; per-bin 0.689-9.51 nJ); `bmi_snn_g32p50` 1.570 nJ (window 1.780; 5,000 annotated bins 1.952 against
2.209 on 200 bins); `bmi_snn_g32p25` 1.209 nJ (window 1.360; annotated 1.411 against 1.582). The 500-bin window sits 12-13 %
above the block mean for every core, as the referee expected from its 20 % higher event rate; the annotated 5,000-bin windows
are 11-12 % below the 200-bin figures for the same reason. The per-bin maximum reaches 4x the mean in bins with event bursts.

### E14 (continued): m12 and min32 at 1.28 V (04:20, 20 Sep)
Both 1.28 V hardenings stalled in detailed routing with the slow-corner repair: m12 at 30 % wrote no routing iteration in 3.7 h
(the stalled-start pattern), min32 at 40 % stopped improving at 9,520 violations after five iterations (2.7 h without a new
iteration). Both were stopped and restarted one policy step lower (m12 20 %, min32 30 %); if these do not converge, E14 stands on
`bmi_snn_sp` alone and the m12/min32 low-voltage figures remain liberty re-evaluations (E5 rows).

### E3 (continued): bmi_snn_m12_s622 decided (04:50, 20 Sep)
The 30 % rerun with the 0.8 ns hold margin stalled at the start of detailed routing exactly like the original attempt (no iteration
in 3 h) and was ended by the watchdog; the policy's 20 % netlist (accepted at 00:54, original hold margin, timing met) is the
measured one. The three per-session m12 netlists therefore sit at 30 % (m12, m12_s131, with the larger hold margin) and 20 %
(m12_s622); the utilization enters the comparison through area only.

### E4 results (04:45, 20 Sep): bmi_snn_sp complete
`bmi_snn_sp` 5,000 annotated bins of indy_20160630_01: 2.802 nJ per bin (bit-exact) against 3.154 nJ on the 200-bin window and
2.365 nJ zero-delay on the full block; glitch factor on the long window 1.18, as on the short one. IHP `bmi_snn_sp` at 20 %:
routing converging (844 violations in the twelfth iteration after 65k at 60 %, 41k at 40 %, 20k at 30 %).

### E14 (continued): bmi_snn_min32 at 1.28 V, 30 % (05:20, 20 Sep)
Routed DRC-clean in 36 min and holds at every corner, but the register-to-register critical path arrives at 287.7 ns at
nom_ss_n40C_1v28 (slack -78.9 ns; -94.7 ns at the max RC corner): the 16-bit dense accumulate of the H=32 core is a 342-cell-deep
chain whose 80 ns at TT 1.8 V become 3.6x longer at 1.28 V / -40 C; the flow's setup repair did not shorten it. The pruned
12-bit core (sp) met 200 ns at 1.28 V with a 47 ns data path. One retry with delay-oriented synthesis (`SYNTH_STRATEGY: "DELAY 0"`,
`LV_EXTRA_YAML`); if that fails, the H=32 core keeps its liberty re-evaluation row (1.45 nJ, f_max 18.2 MHz at 1.28 V) and E14
reports that it needs a pipelined accumulate to be hardened at 1.28 V.

### E1 (continued): bmi_snn_lmem (05:30, 20 Sep)
The optional 20-bit latch-memory core (about 400k instances) did not route at 5 MHz within the policy: 30 % aborted at 26,272
violations after 4 iterations (8 h), 20 % at 92,394 after 3 iterations (4.5 h; the lower density spreads the latch rows and
lengthens the row-select and read wiring). As E1 allows for the optional cores, `bmi_snn_lmem` keeps its 50 MHz figures in the
tables, marked as such; `bmi_snn_scmem` (register file, 600k instances) is the last optional attempt in that queue.

### E14 (continued): bmi_snn_m12 at 1.28 V, 20 % (06:00, 20 Sep)
Routed DRC-clean in 75 min, setup met at every corner including 1.28 V (+112.8 ns), but hold fails by 1.36 ns on 19 endpoints at
max_ss_n40C_1v28 (and by 0.23 ns at max_ff): the clock through the nested clock gates arrives late at the slow corner and the
0.8 ns hold margin of the TT hardening is not enough there; 48,208 cells against 30,957 for the TT netlist. One retry with a
2.0 ns hold-repair margin at the same utilization.

### E14 result: bmi_snn_min32 hardened at 1.28 V (06:10, 20 Sep)
With delay-oriented synthesis (`SYNTH_STRATEGY: "DELAY 0"`) at 30 % the H=32 core meets 200 ns at 1.28 V / -40 C (setup and hold
positive at all twelve corners, DRC-clean, 64 min): the accumulate chain that arrived at 288 ns with the area-oriented netlist is
restructured; cell count and area against the TT netlist below. The annotated 200-bin measurement at the 1.28 V corner follows
(`sim/measure_lowv.sh`).
Figures: setup +113.1 ns at nom_ss_n40C_1v28 (data path 87 ns against 288 ns before), hold +2.63 ns there and +0.114 ns at
max_ff; 31,632 cells / 0.1752 mm2 against 16,744 cells / 0.1194 mm2 for the TT-signoff netlist (+89 % cells, +47 % area): the
1.28 V signoff of the dense 16-bit core is paid in restructured, upsized logic.

### E5 result: GF180 latch-memory core hardened (06:50, 20 Sep)
`pdk_gf180/bmi_snn_lmin2` at 30 % with the 0.8 ns hold margin: DRC-clean after 8 h (routing 26,518 -> 758 -> 11 -> 0 violations),
timing met at every corner (hold +0.093 ns worst), 208,138 cells / 5.15 mm2. Its 500-bin zero-delay window and idle run start
(`sim/measure_pdk5.sh gf180 lmin2 func`); an annotated run of this size is attempted only if the sky130 E9 run shows that Icarus
can handle the annotated latch memory within the budget.

### E14 measurement (07:05, 20 Sep): bmi_snn_min32 hardened at 1.28 V
Annotated 200-bin run at nom_ss_n40C_1v28 (bit-exact): 2.37 nJ per bin against 4.18 nJ for the TT netlist at 1.8 V (1.77x);
leakage 0.122 uW at -40 C, average power at 250 bins/s 0.714 uW. The TT netlist re-evaluated at 1.28 V on its annotated window
gives 1.78 nJ (setup slack 145 ns, f_max 18 MHz without IO constraints): the timing-safe 1.28 V hardening costs 33 % more energy
than the liberty swap because of its 89 % more cells. Together with sp (1.43 nJ against 3.15 nJ, 2.2x) the two hardened
low-voltage cores confirm the direction of Table A2 but with a smaller gain than the swaps suggested. m12 at 1.28 V (20 %, 2.0 ns
hold margin) is the last E14 run in flow.

### E5 result: GF180 latch-memory core measured (07:20, 20 Sep)
500-bin window of indy_20160630_01 bit-exact: 42.2 nJ per bin at 5 V (sp on the same kit: 23.8 nJ), leakage 49.6 uW (the
latch array: 134,639 logic cells against 18,951 for sp; 4.83 mm2), average power at 250 bins/s 60.2 uW, i.e. the leakage of the
standard-cell weight memory dominates at 5 V just as the 1.3 uW of the sky130 latch memory did at 1.8 V. Supply re-evaluations
(3.3 V, 1.8 V, ss 1.62 V) follow.
(Leakage split of the GF180 latch core: 32.5 uW in the logic cells, 17.1 uW in fillers and taps; 23.8 cycles per bin.)

### E1/E9 (continued): sky130 latch-memory core at 20 % (07:50, 20 Sep)
`bmi_snn_lmin2` at 20 % routed DRC-clean (265 min, 220,358 cells / 1.77 mm2) and meets setup, but 394 endpoints fail hold
(-0.475 ns at max_ff, -0.304 ns at nom_tt, -0.079 ns at max_ss) with the 0.3 ns hold margin of its 50 MHz configuration: the
161 row clock gates of the latch memory put every row's write path one clock-gate delay behind the data. Repeated at 20 % with a
1.0 ns hold margin (tag `bmi_snn_lmin2_5m_u20h`; the GF180 latch core passed with 0.8 ns); the E9 annotated glitch run waits for it.

### E4 / E5 results (07:50, 20 Sep): min32 complete, GF180 latch core at other supplies
`bmi_snn_min32`: full block 3.068 nJ per bin (window 3.457, +13 %), 5,000 annotated bins 3.709 nJ (200-bin window 4.181),
per-bin 0.90-11.8 nJ, all bit-exact. GF180 `bmi_snn_lmin2` re-evaluated: 17.1 nJ at 3.3 V (leakage 22.9 uW), 4.67 nJ at 1.8 V
(7.86 uW, f_max 78 MHz), 4.17 nJ at the ss 1.62 V / 125 C corner (dynamic 3.70 nJ, leakage 98.5 uW at 125 C).

### E14 result: bmi_snn_m12 hardened at 1.28 V (08:00, 20 Sep)
At 20 % with a 2.0 ns hold-repair margin the 12-bit gated core meets 200 ns at 1.28 V / -40 C with positive hold at every corner
(135 min, DRC-clean); figures below against the TT netlist (30 %). All three E14 cores are now hardened at 1.28 V (sp 40 %,
min32 30 % with delay synthesis, m12 20 % with the larger hold margin); m12's annotated measurement at the 1.28 V corner follows.
| netlist | util | cells | area (um^2) | setup slack ss_n40C_1v28 (ns) | hold slack ff_n40C_1v95 (ns) |
|---|---|---|---|---|---|
| bmi_snn_m12_5m (1.8 V signoff) | 30 % | 32,603 | 239,629 | +125.8 (re-evaluated with the 1.28 V liberty) | +0.20 |
| bmi_snn_m12_5m_lv (1.28 V signoff) | 20 % | 55,518 | 375,337 | +89.8 | +1.17 |

The 1.28 V netlist has 70 % more cells and 57 % more area than the TT netlist (hold buffers dominate: a 2.0 ns margin was
needed for the fast corner). The setup slack is comfortable (90 ns of 200 ns), so the core would also close at 1.28 V at a
higher clock; only the hold repair drives the area.

### Policy acceptance: bmi_snn_g128p25 at 30 % (07:54, 20 Sep)
50 % and 40 % were stopped by the watchdog (detail route at 44 and 20 k violations after four iterations); 30 % closed in 35 min,
DRC-clean, 51,113 cells, 356,233 um^2, worst setup slack +117.5 ns (ss_100C_1v60), hold +0.093 ns (ff_n40C_1v95). The pipeline
(full block B, then 20,000-bin A/C blocks) starts automatically. `bmi_snn_g128` (dense H = 128) is the last core in the grid
queue and starts at 50 %.

## Figures (continued): F1-F3 brought to the requested layout (2026-09-20, 08:20)
- F1 `figures/fig_pareto.py`: x = three-session mean R2 (linear 0.50-0.62), y = annotated energy per bin (log 1-3000 nJ); marker
  shape = weight storage (constants / latches / SRAM block / software), colour = H; labels "64, 25 %"; horizontal min-max bars over
  the five seeds; a line per H across densities and a dashed line through the dense cores across H; vertical lines at 0.55 and
  0.593 (NeuroBench SNN2). Reference points: SRAM core in event and dense mode, gated SRAM core, the 16-bit hardwired cores, the
  latch-memory core (50 MHz netlist until the 5 MHz hardening closes, marked in the label) and the hand-tuned software at 5 MHz.
  18 points with g128p25 (zero-delay until its annotated run finishes). Data: `figures/pareto_points.csv`.
- F2 `figures/fig_pavg_vs_rate.py`: two panels (sp, min32), one line per kit and flavour: sky130 1.8 V, sky130 1.8 V with the
  interpolated 37 C leakage (dotted), sky130 1.28 V (E14 netlist, annotated, -40 C slow liberty), GF180MCU 5 V and 1.8 V
  (re-evaluated netlist, zero-delay energy times the kit glitch factor 1.08), NanGate45 (zero-delay), ASAP7 SRAM-Vt and RVT; IHP
  is added automatically once `ihp/sp` exists in pdks5.json. Vertical dashed line and a marker on every line at 250 bins/s.
  Data: `figures/pavg_vs_rate.csv` (energy kind stated per row).
- F3 `figures/fig_power_breakdown5.py`: added the SRAM core's dense mode (367 nJ annotated) as its own bar; the latch core
  appears once E9 delivers its annotated 5 MHz run; totals printed above the 37 C marker.
- All scripts now write PDF and PNG both to `paper/figures/` (used by the manuscript) and to `figures/` (deliverable folder,
  next to the CSVs). `sw/fig_accuracy.py` (F5) does the same for `r2.pdf`.

## E1/E5 (continued). Policy bookkeeping (2026-09-20, 08:40)
`sw/policy_summary5.py` (called by `sw/refresh_round5.sh`) parses `logs/policy_round5.log` and `logs/orfs5_policy.log` into
`results/POLICY5.md` / `results/policy5.json`: the accepted utilization of every kit/design pair, the full attempt sequence
(utilization: outcome, `h` = hold-margin rerun, `lv` = 1.28 V signoff) and, per attempt, runtime and the reason for a rejection
(watchdog message, DRC, timing). At the time of writing: 46 kit/design pairs, 40 with an accepted run, 116 attempts. The stray
`0` lines in the policy log came from `grep -c ... || echo 0` printing twice when no PASS line exists (fixed in the three policy
scripts; the summariser ignores such lines).

### E3 result: bmi_snn_min32_s131 pipeline complete (08:31, 20 Sep)
Session C netlist of the H = 32 core (50 %): full block 52,116 bins, 3.71 events/bin, 2.57 nJ/bin zero-delay (16.6 cycles/bin);
annotated 5,000-bin window 3.08 nJ/bin; bit-exact. Compare the session-B netlist: 3.07 / 3.71 nJ at 4.88 events/bin. The
per-session table (`results/per_session.csv`, `paper/numbers_persession.tex`) now has B and C complete for sp and min32; the
session-A blocks (132,745 bins) and the m12 blocks are still running.

### E3/E4 result: bmi_snn_sp_s622 full block of session A (08:50, 20 Sep)
Session-A netlist of the pruned core (40 %): whole test block, 132,745 bins at 7.93 events/bin, 3.25 nJ/bin zero-delay, bit-exact
(16 h streamed simulation on the loaded machine). The 50 MHz transfer model of the earlier rounds predicted 3.59 nJ at this
session's mean rate; scaled by the 50 -> 5 MHz change of the pruned core (2.93 -> 2.67 nJ, 0.91x) it gives 3.27 nJ, within 1 % of
the measurement. The three-session set of the pruned core (zero-delay, own weights): A 3.25 (7.93 ev/bin), B 2.36 (4.88), C 1.77
(3.71) nJ/bin; a straight line through the three (different netlists, so indicative only) gives 0.59 nJ + 0.34 nJ per event.
The 5,000-bin annotated window of A has started.

### E14 result: bmi_snn_m12 measured at 1.28 V (08:55, 20 Sep)
The 1.28 V netlist (20 %, 2.0 ns hold margin, 55,518 cells) decodes bit-exactly (200 annotated bins, 500 zero-delay bins) at
ss_n40C_1v28: 4.42 nJ/bin annotated (3.05 zero-delay), leakage 0.195 uW, P_avg at 250 bins/s (clock
stopped) 1.30 uW. Against the same core at 1.8 V (30 %, 32,603 cells): 6.90 nJ annotated (5.20 zero-delay), leakage
0.362 uW, P_avg 2.09 uW, i.e. 1.56x less energy per bin and 1.61x less average power. The gain is smaller than for sp
(2.2x) and min32 (1.76x) because the 2.0 ns hold margin needed at the fast corner added 70 % cells, mostly hold buffers on the
gated clock paths, whose switching is charged to the annotated energy. E14 is complete for the three requested cores:

| core | 1.8 V netlist: util / cells / E_ann nJ / P_avg uW | 1.28 V netlist: util / cells / E_ann nJ / leak uW / P_avg uW | energy ratio |
|---|---|---|---|
| bmi_snn_sp | 40 % / 24,546 / 3.15 / 1.03 | 40 % / 32,484 / 1.43 / 0.073 / 0.43 | 2.2x |
| bmi_snn_min32 | 50 % / 16,744 / 4.18 / 1.19 | 30 % (delay synthesis) / 31,632 / 2.37 / 0.122 / 0.71 | 1.76x |
| bmi_snn_m12 | 30 % / 32,603 / 6.90 / 2.09 | 20 % (hold margin 2.0 ns) / 55,518 / 4.42 / 0.195 / 1.30 | 1.56x |

### E2/E4 result: bmi_snn_g64p125 pipeline complete (08:57, 20 Sep)
H = 64 at 12.5 % synapses (50 %): full block B 1.58 nJ/bin over 107,444 bins, annotated 5,000-bin window 1.82 nJ/bin
(500-bin window 1.76, 200-bin annotated 2.02). Mean R2 0.528 (5 seeds), below the 0.55 gate: the cheapest H = 64 point but not
a usable one. Grid cores with complete pipelines: g16p50, g32p25, g32p50, g64p125; running: g64p50, g128p125, g128p25; g128 hardening.

### E2 result: bmi_snn_g128p25 windows (08:59, 20 Sep)
H = 128 at 25 % synapses (30 %, 51,113 cells, 0.356 mm2): 5.74 nJ/bin zero-delay, 7.0 nJ annotated (glitch factor 1.22), leakage
0.668 uW, P_avg 2.42 uW at 250 bins/s; mean R2 0.572 (5 seeds), the same accuracy as the H = 64 / 25 % core (0.573) at 2.2x its
energy, so it does not reach the front. Its full block B (107,444 bins) has started. F1 refreshed (18 points).

### E14 finding: re-evaluation against re-hardening at 1.28 V (09:05, 20 Sep)
With the m12 measurement in, all three cores can be compared both ways. The netlists signed off at 1.8 V (nine corners) also meet
200 ns when re-evaluated with the ss_n40C_1v28 liberty, with room to spare, and their hold slack at that corner is positive:

| core | 1.8 V netlist re-evaluated at 1.28 V: setup / hold slack (ns), f_max (MHz), E_ann (nJ), leak (uW) | netlist hardened with 1.28 V signoff: E_ann (nJ), leak (uW), cells vs 1.8 V netlist | hardened / re-evaluated |
|---|---|---|---|
| bmi_snn_sp | +142.9 / +2.42, 17.5, 1.34, 0.086 | 1.43, 0.073, +32 % | 1.07x |
| bmi_snn_min32 | +145.2 / +2.80, 18.2, 1.78, 0.049 | 2.37, 0.122, +89 % | 1.33x |
| bmi_snn_m12 | +125.8 / +2.99, 13.5, 3.13, 0.136 | 4.42, 0.195, +70 % | 1.41x |

The re-hardened netlists are 7-41 % more expensive in energy per bin (and up to 2.5x in leakage) than the re-evaluated ones. The
extra cost is not the 1.28 V corner itself but the hold repair the twelve-corner signoff demanded: the fast corner (ff_n40C_1v95)
combined with the slow 1.28 V clock tree forces hold buffers on the gated clock paths (sp needed the default margin, min32 delay
synthesis, m12 a 2.0 ns margin before the run converged), and their switching is charged to the annotated energy. Since the 1.8 V
netlists already pass every characterised corner including ff_n40C_1v95, the re-evaluated numbers are legitimate operating points of
a netlist that works at both supplies, and the re-hardened numbers are the conservative bound for a part designed for 1.28 V only
under this flow's signoff set. Both are kept: `results/corners5.json` (`tt.e_lowv` re-evaluated, `lv.e_sdf_1v28` re-hardened),
`paper/corners_table5.tex` / `numbers_corners5.tex`; F2 draws the re-hardened (conservative) 1.28 V line and says so in its CSV.

### E1: bmi_snn_scmem at 40 % stopped by the watchdog (09:25, 20 Sep)
The register-file core (flip-flop weight memory, 88 k logic cells) at 40 %: detailed routing 214 k -> 101 k -> 94 k violations after
four iterations, aborted by the watchdog after 250 min; the policy continues at 30 % and 20 %. In rounds 1-4 this core only routed at
25 % with a 34 % placement density and missed the slow corner by 2.6 ns at 20 ns; at 200 ns timing is not the issue, pin access in the
weight array is. `bmi_snn_hw` (hardwired 20-bit) at 40 % is converging: 95 violations after 13 router iterations.

### E3 result: bmi_snn_m12_s131 full block of session C (10:00, 20 Sep)
Session-C netlist of the 12-bit gated core (30 %): 52,116 bins at 3.71 events/bin, 3.65 nJ/bin zero-delay, bit-exact. Its 500-bin
window on the same session (3.63 events/bin) gave 3.60 nJ, so the whole block confirms the window within 1.5 %; the session-B
netlist on its own stream costs 5.20 nJ at 5.87 events/bin (500-bin window), the session-A netlist 6.31 nJ at 7.47 events/bin.
The 5,000-bin annotated window of C has started.

### E1/E9: bmi_snn_lmin2 hold-margin rerun killed by the watchdog, relaunched with relaxed thresholds (10:15, 20 Sep)
The 20 % rerun with a 1.0 ns hold-repair margin was stopped by the watchdog at 93 k violations after four router iterations
(228 k -> 105 k -> 93 k). The earlier 20 % run without the margin had the same start (224 k -> 102 k -> 92 k) and then converged
(15 k -> 1.2 k -> 82 -> ... -> 0 after 21 iterations, DRC-clean but hold -0.48 ns at the fast corner), so the rule "more than 20 k
violations after three iterations" is wrong for this 220 k-cell latch array: its first iterations only tidy the row and column
buses. The thresholds are now environment variables (`WD_VIOL3`, `WD_VIOL8`; defaults unchanged) and the run was relaunched with
`WD_VIOL3=400000 WD_VIOL8=60000` (the 3 h no-progress rule stays); log `logs/harden_bmi_snn_lmin2_20h_retry.log`. The E9
waiter picks the accepted run up automatically. The same watchdog shape stopped `bmi_snn_scmem` at 40 % (214 k -> 101 k -> 94 k);
its policy continues at 30 % and 20 % with the default thresholds, and the register-file core keeps its 50 MHz figures if those fail.

### E3 complete for the pruned core (10:47, 20 Sep)
bmi_snn_sp_s622 annotated 5,000-bin window of session A: 3.86 nJ/bin (full block zero-delay 3.25, ratio 1.19, the usual sky130
glitch factor). The pruned core is now complete on all three sessions with its own weights (full block zero-delay / 5,000-bin
annotated): A 3.25 / 3.86 (7.93 events/bin), B 2.36 / 2.80 (4.88), C 1.77 / 2.04 (3.71); `results/per_session.csv`,
`paper/numbers_persession.tex` updated. Pipelines still running: min32_s622 (A), m12 (B), m12_s622 (A), m12_s131 (C annotated),
g64p50, g128p125, g128p25, ming, min, top/topg blocks.

### Policy acceptance: bmi_snn_hw at 40 % (12:00, 20 Sep)
The hardwired 20-bit core (64 lanes, dense logic kept) closed at 40 % after 290 min: the router went 42 k -> 8 k -> 1.2 k -> 95
violations in 13 iterations, then sat on a single violation from iteration 25 to 39 and cleared it at iteration 40 (each late
iteration took about 30 min). DRC-clean, 40,562 cells, 0.286 mm2, worst setup slack +116.8 ns (ss_100C_1v60), hold +0.316 ns
(ff_n40C_1v95); at 50 MHz the same core needed 88,404 cells and 0.441 mm2 (28 % utilization hedge run). 60 % and 50 % were
stopped by the watchdog (122 k and 23 k violations after 3-4 iterations). Its pipeline (500/200-bin windows, idle, full block B,
5,000-bin annotated) started at 12:01.

### E2: bmi_snn_g128 at 50 % stopped, policy relaunched at 30 and 20 % (12:27, 20 Sep)
The dense H = 128 core at 50 % never finished its second router iteration: 728 k violations after iteration 0, 769 k at 50 % of
iteration 1 with no output for two hours while the machine ran four routers and 19 simulators (load 90, 14 GB free). The run was
stopped by hand (recorded in the policy log as a rejection with the reason) and the policy relaunched with the list "30 20": the
25 %-synapse H = 128 core needed 30 %, and a 40 % attempt of a core with twice its synapse logic would only have cost another
watchdog cycle. This is the one deliberate deviation from the 60 -> 20 stepping; `results/POLICY5.md` shows it.

### E1 result: bmi_snn_hw windows at 5 MHz (12:34, 20 Sep)
Hardwired 20-bit core (40 %): 8.35 nJ/bin zero-delay on the 500-bin window (21.0 cycles/bin, latency 1.0 us), leakage 0.417 uW,
idle 3.95 uW with the clock running, P_avg 2.50 uW at 250 bins/s with the clock stopped. At 50 MHz: 9.81 nJ zero-delay
(12.1 annotated), leakage 0.674 uW. The annotated windows (event and dense mode) and the full block B are running.

### E1/E9: bmi_snn_lmem2 at 30 % stopped by the default watchdog, relaunched with the relaxed thresholds (12:45, 20 Sep)
The latch-memory core with the pipelined W2 read (lmem2, 16-bit state) at 30 %: 268 k -> 136 k -> 126 k violations after three
router iterations, killed by the default rule after 310 min. This is the same routing shape as lmin2 at 20 % (224 k -> 102 k -> 92 k,
then converging to 0 in 21 iterations), so the policy instance (which would have stepped to 20 % with the same thresholds) was
stopped and relaunched at 30 % then 20 % with `WD_VIOL3=400000 WD_VIOL8=60000` and the 1.0 ns hold-repair margin from the start
(tag suffix `h`; lmin2 without the margin failed hold by 0.48 ns at the fast corner). Log `logs/harden_bmi_snn_lmem2_30h_retry.log`;
the lmem2 pipeline waiter picks the accepted run up.

### E3 result: bmi_snn_m12_s131 pipeline complete (12:49, 20 Sep)
Session-C netlist of the 12-bit gated core: annotated 5,000-bin window 4.84 nJ/bin (full block zero-delay 3.65, ratio 1.33, the same
glitch factor as the session-B netlist's 500/200-bin windows, 6.90 / 5.20; the gated 12-bit datapath glitches more than the pruned core's 1.19).

### Policy acceptance: bmi_snn_scmem at 30 % (12:50, 20 Sep)
The register-file core (flip-flop weight memory) closed at 30 % in 215 min: router 164 k -> 69 k -> 64 k -> 5.4 k -> 308 -> 22 -> 0
violations in seven iterations, DRC-clean, timing met at all nine corners (worst setup slack +77.4 ns at ss_100C_1v60, hold
+0.516 ns at ff_n40C_1v95): 301,258 cells, 2.68 mm2. At 50 MHz this core needed 511,493 cells and 3.23 mm2 and missed the slow
corner by 2.6 ns; at 200 ns it is the first fully timing-clean register-file netlist of the project. Its pipeline (500-bin windows,
idle, then 5,000-bin zero-delay windows on the three sessions with each session's weights; no SDF, the annotation of the
flip-flop memory does not complete in Icarus) started at 12:51. Note for the watchdog: with 64 k violations after three
iterations this run sat above the default 20 k rule and survived only because the fourth iteration (5.4 k) finished within the
5-minute polling interval; the relaxed thresholds introduced for lmin2/lmem2 are the right setting for the memory cores.

### E5: IHP driver split (13:00, 20 Sep)
The sequential IHP driver (sp -> m12 -> min32 -> min16 -> lmin2) has spent 11 h on sp at 20 % (router at 187 violations after 19 of
40 iterations, still falling). With the machine load back to 40 after the g128 and lmem2 restarts, the driver loop was stopped (the
sp run itself continues as its own process) and `bmi_snn_min16` was started in parallel with the list "30 20" (sp needed 20 %;
the smaller core may close at 30 %). m12 and min32 follow the same way when a slot frees; IHP lmin2 is not attempted (the ORFS
latch-memory runs ran out of memory on NanGate45/ASAP7, see above). Log `logs/orfs5_ihp_min16_driver.log`.

### E4 interim: SRAM cores across the three sessions (13:00, 20 Sep)
`bmi_snn_top` (event mode, weights of each session loaded), 5 MHz, vdd-only SRAM liberty: 20,000-bin zero-delay windows A 47.4 nJ/bin
at 8.48 events/bin (229 cycles/bin), C 28.6 nJ at 3.78 events/bin (149 cycles/bin); the 500-bin window of B (35.9 nJ at 5.87
events/bin) lies 3 % below the straight line through A and C (predicted 36.9). The line is 13.5 nJ + 4.00 nJ per event: the same
slope as the 50 MHz transfer model of the earlier rounds (16.8 + 4.00 n_ev) with the intercept lowered by the clock change, i.e.
the per-event cost of the sequential core is clock-independent and the fixed per-bin cost fell by 20 %. Annotated 2,000-bin windows:
A 55.4 (9.26 events/bin), B 40.1 (5.56), C 31.9 (3.62) nJ/bin; against the zero-delay windows of the same sessions the ratios are
1.12-1.17, indicative only because the 2,000-bin windows have a different event rate than the 20,000-bin ones (the same-window
glitch factor of the core is 1.21 from the 500/200-bin E1 windows). `bmi_snn_topg` (gated membrane groups): C 21.8 nJ zero-delay (20,000 bins), annotated A 42.9 / B 30.2 / C 23.3 nJ/bin.
The full B blocks (107,444 bins) of top and topg and topg's A window are still running (top's since 19:00 yesterday: 18 h on the
loaded machine). `results/explore/transfer5.json`, `paper/numbers_transfer5.tex` updated.

### E1 result: bmi_snn_hw annotated windows (13:11, 20 Sep)
Hardwired 20-bit core at 5 MHz: 10.2 nJ/bin annotated (glitch factor 1.23; 50 MHz: 12.1), dense mode 45.0 nJ zero-delay / 48.6
annotated, P_avg 2.98 uW at 250 bins/s with the clock stopped (50 MHz: 3.13). Full block B (107,444 bins) started. F3 now shows the
core as its own bar (10 bars).

### E1 result: bmi_snn_scmem windows at 5 MHz (13:29, 20 Sep)
Register-file core (30 %, 2.68 mm2, timing met at all corners): 10.2 nJ/bin zero-delay on the 500-bin window (22.6 cycles/bin,
latency 1.4 us), dense mode 45.8 nJ, leakage 4.86 uW (1.07 uW in logic cells), idle 9.2 uW with the clock running, P_avg 7.41 uW at
250 bins/s with the clock stopped. At 50 MHz (timing not met at the slow corner): 11.5 nJ, leakage 5.68 uW, P_avg 8.55 uW, dense
52.6 nJ. No annotated run (Icarus does not finish the SDF annotation of the 300 k-instance netlist); the 5,000-bin zero-delay windows
on the three sessions (each with its own weights) are running.

### Policy acceptance: bmi_snn_lmin2 at 20 % with the 1.0 ns hold margin (13:41, 20 Sep)
The relaunch with the relaxed watchdog closed: router 228 k -> 105 k -> 93 k -> 14 k -> 902 -> 71 -> 15 -> 9 -> 8 -> 4 -> 0 violations
in eleven iterations (50 min), DRC-clean, hold met at every corner (+0.42 ns at ff_n40C_1v95, +1.00 at TT, +2.63 at
ss_100C_1v60), setup reported as 0.000 at all corners (latch time borrowing, as in rounds 1-4). 227,127 cells, 1.84 mm2; at 50 MHz
the core needed 367,376 cells and 2.12 mm2 and failed setup (-1.16 ns) and hold (-2.14 ns). The default watchdog would have killed
this run at 93 k violations after the third iteration; the run confirms that the memory cores' routers need the relaxed thresholds
(`WD_VIOL3=400000 WD_VIOL8=60000`). The E9 waiter and the lmin2 pipeline (500-bin windows, idle, then 5,000-bin zero-delay windows
on the three sessions) start on this netlist.

### E1 result: bmi_snn_lmin2 windows at 5 MHz (14:03, 20 Sep)
Latch-memory core with gated 12-bit datapath and pipelined W2 read (20 %, 1.84 mm2, hold clean): 6.21 nJ/bin zero-delay on the
500-bin window (23.8 cycles/bin, latency 1.6 us), leakage 4.38 uW (0.85 uW in logic cells; the 20 % floorplan carries more fill and
hold buffers than the 22 % / 50 MHz netlist, whose leakage was 3.65 uW), idle 8.7 uW with the clock running, P_avg 5.93 uW at
250 bins/s with the clock stopped (50 MHz netlist: 6.40 nJ, 5.25 uW). The latch core is the one design whose average power did not
fall with the clock change: its energy per bin is already dominated by the memory read, and the leakage of the larger, hold-repaired
netlist outweighs the small dynamic gain. Its 5,000-bin zero-delay windows on the three sessions are running; the E9 annotated
50-bin run (glitch factor) is compiling.

### E2: bmi_snn_g128 at 30 % restarted with the relaxed watchdog (14:30, 20 Sep)
The dense H = 128 core at 30 % started detailed routing at 190 k violations (g128p25 at the same utilization started at 29 k and
closed in seven iterations; g64p50 at 30 % started at 21 k). The default rule would have stopped it at the third iteration, so the
run was stopped by hand after its first iteration and relaunched with `WD_VIOL3=400000 WD_VIOL8=60000` (list "30 20"); recorded in
the policy log as a manual rejection. Log `logs/harden_bmi_snn_g128_relaunch2.log`.

### E2/E4 result: bmi_snn_g64p50 full block (14:35, 20 Sep)
H = 64 at 50 % synapses (30 %): full block B 3.35 nJ/bin over 107,444 bins, bit-exact (500-bin window 3.81; the block runs 12 %
below the window, as for every core so far, because the first 500 bins of the block carry 5.87 events/bin against the block's
4.88). Its 5,000-bin annotated window has started.

### E5: IHP SG13G2 bmi_snn_min16 accepted at 30 % (14:45, 20 Sep)
The parallel IHP run of the H = 16 core closed at 30 % in 115 min: router 10.5 k -> 5.8 k -> ... -> 13 -> 0 violations in 20
iterations (bounded at 40), DRC-clean, setup slack +119.5 ns at the typical corner (ORFS reports no hold figure), 0.361 mm2
instance area including fill (logic cells and area are taken from the netlist and liberty by the collector, as for the other kits).
Measurement started (`sim/measure_pdk5.sh ihp min16 all`: 500-bin zero-delay window, idle, annotated 200-bin window with the IHP
functional models where the annotation completes, slow 1.08 V / 125 C re-evaluation with f_max); `bmi_snn_min32` started on IHP
with the list "30 20" in the freed slot. IHP sp at 20 % is at 91 violations after 22 of 40 iterations.

### E4 result: bmi_snn_lmin2 5,000-bin window of session B (14:55, 20 Sep)
Latch-memory core, weights of indy_20160630_01: 5.72 nJ/bin zero-delay over 5,000 bins at 5.26 events/bin, bit-exact (500-bin
window 6.21 at 5.87 events/bin). The session-A window (weights of indy_20160622_01) has started; the E9 annotated 50-bin run is
still simulating (started 13:58).

### E5 result: IHP SG13G2 bmi_snn_min16 at 5 MHz (14:50, 20 Sep)
11,468 logic cells, 0.121 mm2, setup slack +119.5 ns: 0.936 nJ/bin zero-delay (sky130: 1.69, i.e. 0.55x; in round 2 at 50 MHz the
ratio was 0.79x), leakage 1.54 uW in logic cells and 16.2 uW in total (the decap/fill cells of the IHP platform dominate, as in
round 2), P_avg 16.4 uW at 250 bins/s with the clock stopped (1.8 uW with logic leakage only). Slow corner 1.08 V / 125 C:
0.73 nJ/bin, leakage 10.6 uW, f_max 894 MHz (the small core is far from its speed limit at 200 ns). No annotated run: the kit's
Verilog on this machine is the functional model set generated in round 2 (no timing checks, so an SDF would annotate nothing);
an attempt with the IHP-Open-PDK behavioural models is noted as optional. Bit-exact over 500 bins. `results/PDKS5.md`,
`paper/pdks_table.tex`, `numbers_pdks.tex`, `results/pdks_pavg_vs_rate.csv` refreshed; F2 gains the IHP line once `ihp/sp` exists.

### E5: annotated simulation on IHP SG13G2 now works (15:06, 20 Sep)
Recipe (mirrors the ASAP7 one): SDF written by OpenSTA from the routed netlist, SPEF and the typical liberty
(`power/run_write_sdf.sh`, 200 ns propagated clock); cell models = IHP-Open-PDK `sg13g2_udp.v` (combinational UDPs ihp_mux2/4 that
the cell file references) + `sg13g2_stdcell.v` with its 16 sequential modules removed (`/media/pdk/icarus_sdf_models/
sg13g2_stdcell_seqstripped.v`) + behavioural sequential cells with the vendor pin names and IOPATHs (`sim/ihp_seq_icarus.v`:
dfrbp_1/2, dfrbpq_1/2, lgcp_1; the vendor flip-flops take their state from the `delayed_*` nets of `$setuphold` and stay X in Icarus,
the reason round 2 fell back to functional models). `sim/measure_pdk5.sh ihp <core> sdf` now runs this path.
bmi_snn_min16 on IHP: 200 annotated bins bit-exact, 35,398 IOPATHs annotated, 0.988 nJ/bin against 0.936 zero-delay, glitch factor
1.06 (GF180 1.06-1.11, ASAP7 1.07-1.10, sky130 1.18-1.23). sp, m12 and min32 get the same run when their IHP hardenings close.

### E4 results: bmi_snn_topg session-A window, bmi_snn_g64p50 annotated window (16:00-16:22, 20 Sep)
- `bmi_snn_topg` (gated SRAM core) 20,000-bin zero-delay window of session A: 36.4 nJ/bin at 8.48 events/bin (229 cycles/bin),
  bit-exact; with C (21.8 at 3.78) the line is 10.0 nJ + 3.11 nJ per event (top: 13.5 + 4.00), and the 500-bin B window (26.5) lies
  7 % below the line's prediction. The gating saves 3.5 nJ of the fixed cost and 0.9 nJ per event. Full B blocks of top and topg
  still running (top 21 h, topg 20 h).
- `bmi_snn_g64p50` 5,000-bin annotated window: 4.24 nJ/bin (full block zero-delay 3.35, ratio 1.27). Pipeline complete.

### E2/E4 result: bmi_snn_g128p125 full block (16:24, 20 Sep)
H = 128 at 12.5 % synapses (50 %): full block B 3.38 nJ/bin over 107,444 bins, bit-exact (500-bin window 3.78, ratio 0.89); its
5,000-bin annotated window has started.

### E4 result: bmi_snn_lmin2 5,000-bin window of session A (16:30, 20 Sep)
Latch-memory core with the weights of indy_20160622_01: 8.22 nJ/bin zero-delay at 8.38 events/bin, bit-exact (session B: 5.72 at
5.26). The two points give 1.5 nJ + 0.80 nJ per event for the latch core (the SRAM core: 13.5 + 4.00; the pruned hardwired core across
its per-session netlists: 0.6 + 0.34). The session-C window has started.

### Scheduling note (17:00, 20 Sep)
The IHP sp router (20 h in, 73 violations left after 24 iterations) has been in a single-threaded phase since 15:16 and gets about a
third of a core at load 67; the two OpenLane routers (g128, lmem2) run 24 threads each. Both were reniced by +3 so that the
long-running IHP job and the simulators get their share; nothing was stopped.

### E1/E4 result: bmi_snn_ming full block (17:15, 20 Sep)
Hardwired 16-bit gated core (30 %): full block B 4.54 nJ/bin over 107,444 bins, bit-exact (500-bin window 5.20, ratio 0.87), after
a 20 h streamed simulation. Its 5,000-bin annotated window has started.

### E4 result: bmi_snn_lmin2 pipeline complete (17:29, 20 Sep)
Session-C window (weights of indy_20170131_02): 4.63 nJ/bin at 3.93 events/bin, bit-exact. The three 5,000-bin windows
(A 8.22 at 8.38, B 5.72 at 5.26, C 4.63 at 3.93 events/bin) fit 1.47 nJ + 0.806 nJ per event
(largest residual 0.1 %); the 500-bin E1 window (6.21 nJ at 5.87 events/bin) is predicted at 6.20 nJ (+0.2 %). The latch
core's zero-delay pipeline is complete; only the E9 annotated 50-bin run is still simulating.

### Policy acceptance: bmi_snn_lmem2 at 30 % with the 1.0 ns hold margin (17:35, 20 Sep)
Latch-memory core with 16-bit state and the pipelined W2 read: router 275 k -> 137 k -> 127 k -> ... -> 2 -> 1 -> 1 -> 1 -> 0 in
24 iterations (290 min in total), DRC-clean, hold met at every corner (+0.99 ns at ff_n40C_1v95, +1.66 at TT, +3.54 at
ss_100C_1v60), setup reported 0.000 (latch borrowing). 208,689 cells, 1.82 mm2; at 50 MHz the core needed 385,176 cells and
2.29 mm2 and carried an input-port hold flag. With this, every core of the project except `bmi_snn_lmem` (unpipelined latch
ablation, kept at 50 MHz) and `bmi_snn_g128` (in progress) has a timing-clean 5 MHz netlist. The lmem2 pipeline (500-bin
windows, idle, 5,000-bin windows on the three sessions) starts automatically, and the E9 annotated 50-bin run for lmem2 was
launched (`sim/e9_lmin2.sh bmi_snn_lmem2 50`, log `logs/e9_lmem2.log`; the lmin2 one has been simulating since 13:58).
