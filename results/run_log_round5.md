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
