# Round 10 run log: energy per bin from the tool (real-time runs), per-stage clock gating on every parallel core

Started 8 Oct 2026 23:05. Request: `paper/experiments_round10.md`. Replaced files: `paper/_superseded/2026-10-08_before_round10/`
(the numbers*.tex and table files, the four figures, designs/pdks5/frontend JSON as they were before this round; the paper itself
is not touched in this round). Deliverables: `paper/deliverables_round10/`.

## 0. Mechanics of the real-time measurement

**Testbench timing** (`sim/tb_bmi_snn.v`, `-DREALTIME`, round 10). The oscillator `osc` runs freely at 5 MHz (200 ns); the clock
delivered to the core is `clk = osc & clk_run`. After reset and, for the programmable cores, the weight load through the write port
(both with the clock running, before the measured window), the testbench stops the clock and sets the window start T_start at the
next full clock period. Bin k starts at t_k = T_start + k x 4 ms: the testbench enables the clock in the low phase of the oscillator
(the first rising edge follows 100 ns later), presents the events of the bin one at a time through the `ev_valid`/`ev_ready`
handshake exactly as the stand-alone testbenches of rounds 5 to 7 do (the core raises its clock enable `en_q` on `ev_valid`, so the
first event waits one cycle for `ev_ready`, as after any idle gap), asserts the tick after the last event (`tick`/`tick_ready`
handshake), waits for `out_valid`, then waits until the core reports idle (`core_clk_en === 0 && busy === 0`), lets two more edges
through so that the integrated clock gate has closed in the low phase, and stops the clock in the low phase of the oscillator
(`clk_run = 0`: the clock port stays low, no partial pulse). Nothing happens until t_{k+1}. A bin whose active phase would run past
its slot is counted as an overrun (none occurred: the active phase is 4-6 us for the parallel cores, 60-70 us for the SRAM core in
event mode and 0.36 ms in dense mode, 1.1-2.2 ms for the SoC). After the last bin the testbench waits until T_end = T_start + N x 4 ms.
Dense mode (`-DMODE_DENSE=1`) presents the same events (they set bits of the input vector) and the tick; the core then scans the 97 rows.

**How the clock is stopped per design.** Every sky130 core of this study (the SRAM sequential core, the register-file and latch
cores, the hardwired cores, gated or not) has one integrated clock gate `u_icg` at its clock root whose enable `en_q` is an always-on
register (the paper's "clock stopped between bins"). In the real-time runs the testbench additionally stops the external clock while
`en_q` is low, as the digital front end's oscillator enable does in the system; the core itself is unchanged. The SoC (sky130_vex2_soc)
has its clock-gated sleep (`sleep_ctrl`): the firmware writes the SLEEP register after each bin, the testbench (`sim/tb_fw_bmi_rt.v`)
restarts the external clock at the bin start, pulses `wake` (synchronized on the always-on clock, hence the clock must run first),
waits until `sleeping` is back, lets eight edges through and stops the external clock. The front end (round 6, v3) is a real-time run
by construction (its own oscillator enable).

**Waveform and window.** The waveform of the design scope is streamed through a FIFO into `tools/vcd_toggles` (no VCD stored); it
starts at T_start and a testbench marker toggles at T_start and T_end, so that the first and last timestamps are exactly the window
(T = N x 4 ms; the tool reports the window it saw in the toggle file header). Per pin: the transition count and the high time over T.

**Activity conversion over T** (`power/toggles_to_activity.py`): activity per clock cycle = transitions x 200 ns / T, duty = high
time / T, for every dumped variable: cell pins (`set_power_activity -pins`), top-level ports (`-input_ports`) and nets (the driver
pin). With the clock stopped in the idle time the per-cycle activities are small (the clock pin of a gated flip-flop has about
2 x cycles_per_bin / 20,000 transitions per cycle) and OpenSTA's power = activity / period x energy per transition = transitions / T x
energy, i.e. the average over the whole bin. The OpenSTA commands are those of rounds 5 to 7 (`power/power_toggles_sta.tcl`:
`read_liberty` (sky130_fd_sc_hd tt 1.8 V 25 C; the SRAM22 vdd-only liberty copy for the SRAM core), `read_verilog` of the routed
netlist, `read_spef`, `create_clock -period 200 [get_ports clk]`, `set_propagated_clock`, the activity file, `report_power -digits 6`,
`report_power -instances`); no clock-sense stop (round 6 finding). P_total, P_internal, P_switching and P_leakage are taken from the
report's Total line.

**Clock port and root-clock correction.** OpenSTA refuses the measured activity on the clock port ("Warning: activity cannot be set
on clock ports", checked on the pruned core, 20-bin and 5,000-bin runs) and gives every pin of the root clock network (clock port
-> clock buffers -> the clock pin of the first clock gate and the always-on flip-flops) the activity of the clock definition, i.e. the
full 5 MHz rate over the whole window, while downstream of the clock gate the annotated (measured) activity is used (round 5
finding, Appendix D.3). The existing correction (`power/root_clock_correction.py`, round 5) is applied to every real-time run: the
root network is walked in the routed netlist (sky130 cores: 4 clock buffers, the clock-gate clock pin, 2 to 4 always-on flip-flops),
a second OpenSTA run with all data activities zero (`GLOBAL_ZERO=1 GLOBAL_ZERO_DUTY=0`) gives the clock-driven dynamic power of those
cells at the full rate, and P_corrected = P_reported - (1 - d) x P_clock-driven with d = delivered clock cycles x 200 ns / T, the
measured duty of the clock port. The correction is reported per design (uncorrected P_total, corrected P_total, size); it is 3-4 uW on
the sky130 cores (the root buffers at the full 5 MHz would cost more than the whole core) and is the only correction applied.
Leakage is not touched by it.

**Unannotated pins.** Every variable of the dumped scope is annotated; `sw/annot_coverage.py` counts the design's cell pins that
received an activity directly or through their net's driver: 100 % for every netlist (the only dumped variables without a design
counterpart are the power pins of the cell models). In addition `set_power_activity -input -activity 0 -duty 0` is applied before
the measured activities (`UNANNOTATED_ZERO=1`), so that an unannotated input port would carry zero activity instead of OpenSTA's
default (0.1 transitions per cycle, duty 0.5); with full coverage it changes nothing (checked on the pruned core).

**Derived numbers.** P_avg = corrected P_total; E_bin = P_avg x 4 ms; E_dyn = (P_avg - P_leakage) x 4 ms; P_dyn = corrected
P_internal + P_switching = P_avg - P_leakage; P_leak = P_leakage (reported). Nothing is added by hand.

**Windows.** Hardwired cores: first 5,000 bins of the test block of indy_20160630_01 with cell delays annotated (20.0 s of real time).
SRAM core: 2,000 bins annotated in event mode (8.0 s), 500 bins annotated in dense mode (the dense scan makes the annotated
simulation about 6x slower per bin; a 2,000-bin dense annotated run would take about 70 h) plus 2,000 bins zero-delay in dense mode
and a 100-bin annotated dense run for the consistency check against round 7's 100-bin dense window. Standard-cell memories: 50 bins
annotated (the annotated simulation of these 400k-instance netlists takes 5-9 h for 50 bins, see the wall-clock table) and 5,000
bins zero-delay. SoC: 100 bins (0.4 s). Front end: 500 bins (2.0 s). Kits: 5,000 bins annotated (NanGate45 zero-delay).

**Decap-free fill (E10).** As in round 6 (E3b): the accepted run is restarted at `OpenROAD.FillInsertion` from the state before the
fill step with `DECAP_CELL: []` (`synthesis/refill_nodecap.sh`; run tag `<run>_nodecap`), so that placement and routing are untouched;
the fill-step netlist, the RCX parasitics and the post-fill STA (SDF, timing metrics) are assembled into `final/` (the later checker
steps need the design LEF of the disabled Magic step and stop the partial run). The routing DRC count of the original run is carried
over unchanged (no step after detailed routing is rerun); the post-fill STA gives the slacks of the refilled netlist. The refilled
netlist has the same logic cells, the same nets and the same parasitics as the measured one and differs only in fill cells without
signal pins, so the real-time simulation of the refilled netlist is the one already run (same stimulus, same cells, same waveform);
OpenSTA is rerun on the recorded toggles of the real-time run with the refilled netlist and its parasitics (annotated run, zero-data
run, root-clock correction: `sim/measure_rt_nodecap.sh`). This was checked on the pruned core by simulating the refilled netlist in
real time (500 bins annotated) next to the default fill: see the E10 section. The leakage is split by cell class (logic, fill, decap,
tap, diode) for both fills from the per-instance reports (`sw/leak_classes10.py`, the classification of round 6).

## Notes written during the campaign (9 Oct 2026, 00:00-01:00)

- **Specification v3 (00:36).** The grid of Figure 8 is measured in real time as well (E8, now before E2/E3), every grid point is a
  12-bit gated core (the dense H = 32 and H = 16 points become the E5 cores `bmi_snn_g32` and the new `bmi_snn_g16`, 12/14, per-stage
  gating), the decap-free fill (E10) is run on the grid cores too, and `results/grid_round10.csv` carries the header of the paper's
  `pareto10.csv` (that placeholder file was not found in the paper folder; the header given in the specification is used verbatim,
  with the extra columns after it).
- **ASAP7 leakage is state-dependent.** The first kit result outside the 2 % bound: ASAP7 SRAM-Vt pruned core, real-time P_total
  0.604 uW against the round-7 sum 0.739 uW (-18 %). The whole difference is the leakage term: round 7 took the leakage from the idle
  run (1 bin, then 400,000 idle cycles: 0.719 uW), while the decode runs of the same netlist report 0.516-0.517 uW and the real-time
  run 0.583 uW. The ASAP7 liberty leakage tables are strongly state-dependent (per-input-state values that differ by factors), so the
  leakage depends on the values held in the membrane and output registers: after one bin most registers are zero (the idle run), during
  decoding they hold the running state (decode runs), and the real-time run averages the states over 5,000 bins. sky130, GF180 and
  NanGate45 show no such dependence (sky130 pruned core: 0.2432 / 0.2458 / 0.2438 uW in the idle, decode and real-time runs). The
  real-time value is the one defined by this round (the leakage of the whole bin in the state the core actually holds); the deviation
  is explained, not an error of either chain. The same applies to ASAP7 RVT (idle 3.30 uW, decode 2.35 uW).
- **Memory incidents.** 23:38: the first wave (24 simulations, 5 hardenings) reached 57 GB of the 62 GB; two annotated memory-core
  runs (8-10 GB each) were stopped and requeued. 00:27: the OpenLane detailed routing of `bmi_snn_scmemg` at 30 % was killed by the
  kernel's OOM killer (its log ends at 20 % of the first iteration with 0 violations and 8.3 GB) while the post-fill STA of two
  refills ran 18 corner analyses in parallel (1.3-1.9 GB each) - their parents had been stopped but the corner runs survived as
  orphans. The orphans were killed, the scmemg policy was restarted at 30 % (`bmi_snn_scmemg_5m_u30r`; the 20 % attempt that the
  policy had started meanwhile was aborted after 7 min), and `sim/mem_guard.sh` now pauses the largest simulation when less than
  3.5 GB are available and resumes it above 9 GB. The three memory-core refills (scmem, lmem2, lmin2; 9 parallel corner STAs of
  400k-instance netlists, about 13 GB per refill) are run one at a time after the simulations.

## State-dependent power tables under a stopped clock (found 9 Oct 2026, 01:00)

OpenSTA weights a state-dependent internal-power table (`when : "ce"`, ...) with the time-averaged duty (probability of being 1)
of the condition pins over the analysis window, and treats that probability as independent of the toggling of the pin whose
energy is being evaluated. In a real-time window the clock runs for 0.1-8 % of the time, so the duty of every register-driven
signal is dominated by the value it holds while the clock is stopped; the energy of a clock edge or of a data transition - which
only happen while the clock runs - is then weighted with the idle-state probabilities. The round-7 chain measured over the active
window only (duties of the clocked cycles) and did not have this problem. Where it matters:

- **sky130 standard cells: not affected.** sky130_fd_sc_hd has no `when`-conditioned internal power except the tri-state buffers
  (not used); its 6,244 `when` conditions are all leakage tables, for which the time-averaged duty is the right weight. All sky130
  cores without a macro are therefore evaluated exactly as the policy says (consistency so far within 0.7 %).
- **SRAM22 macro (sequential core, SoC).** The macro clock-pin energy has four `when` states (`we&ce`, `!we&ce`, `we&!ce`, `!we&!ce`).
  In the dense 100-bin zero-delay window of `bmi_snn_top`, ce is high for 7.77 % of the window but for 95.2 % of the cycles in
  which the macro clock toggles (the macro clock runs 8.16 % of the time). OpenSTA charges the read energy with weight 0.078
  instead of 0.952: macro internal power 0.911 uW instead of 5.863 uW, P_total 76.35 uW instead of 81.30 uW (round-7 sum
  81.71 uW: -6.6 % without, -0.5 % with the correction). The correction (`power/macro_state_correction.py`) is a second OpenSTA
  run in which only the macro control pins (ce, we) get the duty conditioned on the macro clock running, duty_cond =
  (duty - v_idle (1 - d_clk)) / d_clk with d_clk = activity(clk)/2 and v_idle the pin's value while the clock is stopped (0 for
  ce and we: the memory is disabled when idle; the inference is checked against the feasibility of both values and, on the
  gated runs below, against the directly measured conditional duty). Nothing else changes (difference outside the macro 0.000 uW).
  It is reported separately, like the root-clock correction: columns `macro_corr_uW`, `p_avg_mc_uW`, `e_bin_mc_nJ`, `e_dyn_mc_nJ` of
  `table2_round10.csv`; the LaTeX body `table2_round10.tex` carries the policy numbers, `table2_round10_statecorr.tex` the same
  rows with the macro correction included (only the SRAM-core and SoC rows differ).
- **Other kits (Table 3).** GF180 (6,587 `when`-conditioned internal-power tables in 169 cells) is unaffected in practice
  (+0.5 % total, +0.7 % E_dyn against round 7). IHP SG13G2 (180 tables in 30 cells, among them the flip-flop clock pins) and
  NanGate45 (2,254 tables in 31 cells) are affected in their dynamic energy (IHP +20 %, NanGate45 +34 % against the round-7
  annotated/zero-delay windows), ASAP7 RVT by +11 % and ASAP7 SRAM-Vt by +8 %; the totals of these kits are dominated by leakage
  (IHP 99 %, NanGate45 99.9 %, ASAP7 97-98 %), so the totals still agree within 0.3 % except for the ASAP7 leakage state dependence
  noted above.
  To quantify and remove the effect without hand-made terms, the toggle counter (`sim/vcd_toggles.c`, option `--gate`) now also
  accumulates every signal's high time while the core's clock enable is 1, and `power/toggles_to_activity.py --gated` converts
  these into duties conditioned on the clock running (the activities, transitions per window, are unchanged). The "conditional
  duty" evaluation (`power/out_<tag>_cond`) gives the dynamic power with the state statistics of the clocked cycles; its leakage
  is not used (leakage accrues over the idle time, for which the time-averaged duty is right). Reported separately as
  `p_dyn_cond_uW`, `e_dyn_cond_nJ`, `p_avg_cond_uW` (= P_leak of the standard run + P_dyn of the conditional run). The kit runs are
  repeated with the gated accounting (same vectors, same netlists; the standard results are bit-identical, deterministic simulation).
- **Per-instance sums.** `report_power -instances` summed over all instances exceeds the `report_power` group total by up to 1 %
  on the largest netlists (IHP pruned core +0.08 %, latch cores +0.5-1 %, all in the leakage column); the deliverables use the
  group total minus the removed root-network power, and the leakage-by-class split (from the per-instance report) is scaled to
  the group leakage (`leak_class_scale` column).

## Incidents of the night of 8/9 October (run log, continued)

- **01:06, measurement scripts edited while their instances were running.** `sim/measure_rt.sh`, `sim/run_gls_stream.sh` and
  `sim/run_riscv_rt.sh` were rewritten in place (gated toggle accounting, post-processing step) while about thirty real-time runs
  were inside their simulation step; the g16 case line had already been added to `measure_rt.sh` in place at 00:38. Bash reads a
  script incrementally, so every running instance resumes at a byte offset that no longer matches: three runs whose simulation
  ended between 01:05 and 01:22 (min32, min32g, dense 40-bin annotated of the ungated SRAM core, g32p25) died with a syntax
  error right after the simulation (toggle files complete, no OpenSTA step). Repair at 01:21-01:24: the three scripts were restored
  to the exact content their instances had started with (same inode; `run_gls_stream.sh` verified byte-identical to the committed
  version); because the two groups of `measure_rt.sh` instances (started before and after 00:38) differ by one 59-byte line, the
  g16 case line was removed and a 59-byte comment inserted after the simulation command, so that both groups resume on a valid
  line. The new logic lives in `sim/measure_rt_g.sh`, `sim/run_gls_stream_g.sh`, `sim/run_riscv_rt_g.sh` (gated toggle file,
  `sim/rt_post.sh`), used for every run started afterwards; `sim/measure_rt_pdk.sh` (no instance running) calls the gated streaming
  script directly. Interrupted runs are completed from their toggle files by `sim/rt_finish.sh` (OpenSTA, zero run, root-clock
  correction, coverage, post-processing; the simulation wall-clock is then taken from the file times), which the nodecap watcher
  (`sim/nodecap_watch10.sh`) applies to every finished simulation without a result. The four runs started after the edit (the gated
  validation runs and `lmem2` sdf 50) were stopped and relaunched (01:23); one orphaned `vvp` of the stopped `lmem2` run (5 GB)
  was found and killed at 01:26. The runs that resumed after the repair completed normally (g48p25 01:26, dense 40-bin of the gated
  SRAM core 01:26, g64p125 01:19).
  After the campaign (13 Oct) the three `_g` scripts were folded back into `sim/measure_rt.sh`, `sim/run_gls_stream.sh` and
  `sim/run_riscv_rt.sh` (the gated toggle file is written only when `TOGGLE_GATE` is set, which `measure_rt.sh` and
  `run_riscv_rt.sh` do by default), and the one-off launcher `sim/deferred_scmemg.sh` was removed.
- **01:26, `bmi_snn_scmemg` at 30 % (second attempt, u30r) crashed:** OpenROAD received SIGSEGV in the global routing after
  diode insertion (the first global routing of the same run had completed), while the machine had 0 GB free and 10 GB available.
  The policy stepped to 20 % on its own; that run was stopped after its synthesis started (20 % is not wanted: the ungated
  register-file core is accepted at 30 %, and a 20 % die of this 300k-cell core would not be comparable). A third 30 % attempt
  (tag u30r2) starts automatically when more than 32 GB are available (`sim/deferred_scmemg.sh`).

### Validation of the two state corrections (9 Oct, 01:35)

Three runs were repeated with the gated toggle accounting (`vcd_toggles --gate tb_bmi_snn/u_dut/core_clk_en`):

| run | standard evaluation | conditional-duty evaluation | reference |
|---|---|---|---|
| sky130 pruned core, 500 bins annotated (control) | internal 3.312739 uW, switching 0.878573 uW, leakage 0.2438 uW | internal 3.312741 uW, switching 0.878573 uW (identical to 7 digits), leakage 0.2458 uW (not used) | sky130 cells have no state-dependent internal power: the dynamic power must not change, and it does not |
| sky130 SRAM core, dense, 100 bins zero-delay | P_total corrected 76.39 uW; with the inferred macro correction (+4.951 uW) 81.34 uW | 81.35 uW (ce duty measured directly while the clock enable is 1: 0.951713 = the inferred value 0.951713) | round-7 sum 81.71 uW (-0.4 %) |
| IHP pruned core, 500 bins annotated | P_dyn 0.7225 uW (E_dyn 2.890 nJ), +27 % above the round-7 5,000-bin value | P_dyn 0.6118 uW (E_dyn 2.447 nJ) | round 7: 2.269 nJ over 5,000 bins; the first 500 bins carry 7.2 % more activity than the 5,000-bin average (sky130 pruned core: 3.010 vs 2.807 nJ), so the 500-bin expectation is 2.43 nJ: +0.6 % |

The conditional-duty evaluation therefore reproduces the round-7 chain for a kit with state-dependent tables and leaves sky130
untouched; the inferred SRAM-macro correction equals the directly measured one. All kit runs of Table 3 are repeated with the
gated accounting (the standard results are bit-identical, so nothing already reported changes); the table carries the standard
numbers as the policy asks and the conditional-duty numbers next to them.

### Morning of 9 October: what the night produced, and two corrections to the method notes above

- **Root-network registers (correction of the root-clock correction, 09:45).** The root-clock correction scales the clock-driven
  power of the cells between the clock port and the first clock gate by the duty. For the clock buffers and the gate the
  zero-data run gives that power exactly; for the one or two registers clocked from the root network (the enable register
  `en_q`, the write-enable register of the memory cores) it does not: with every duty forced to 0 the register's clock-pin tables
  are evaluated in an impossible state (D = 0 and QN = 0), which gives 0 W for the NanGate45 DFF and a value 18 % below the
  annotated one for the ASAP7 flip-flop, so too little was removed and the register's full-rate clock power (137 pJ per bin on
  NanGate45, 3.7 pJ on ASAP7, 0.45 nJ on IHP) stayed in E_dyn. Since such a register toggles a few times per bin, its internal
  power in the annotated run is the full-rate clock-pin energy itself; `power/root_clock_correction.py` now scales that value by
  the duty directly for root registers (`di = i`). Effect: sky130 cores unchanged (< 1e-5 uW), NanGate45 E_dyn 0.5435 -> 0.4061 nJ
  (round 7: 0.4055, +0.1 %), IHP E_dyn 2.728 -> 2.279 nJ (round 7: 2.269, +0.5 %), ASAP7 RVT 0.0913 -> 0.0876 nJ (round 7
  0.0822, +6.6 %), ASAP7 SRAM-Vt 0.0857 -> 0.0820 nJ (+2.9 %). All JSONs were regenerated in place (`sw/recorrect_root10.sh`).
  The paragraph on IHP and NanGate45 above therefore overstated the role of the state-dependent tables: after this fix the
  standard evaluation of IHP, NanGate45 and GF180 agrees with round 7 within 0.7 % without the conditional-duty evaluation.
  The conditional-duty evaluation remains the right check for state-dependent libraries; it changes IHP by +0.2 %, GF180 by
  -0.4 %, NanGate45 by -2.5 %, ASAP7 by -1 %, and it is reported next to the standard numbers.
- **ASAP7 residual.** The ASAP7 RVT dynamic energy stays 5.6 % (conditional duties) to 6.6 % (standard) above the round-7
  value, the SRAM-Vt variant 2.0 % to 2.9 %. The absolute difference is 0.005 nJ per bin against a leakage energy of 10.6 nJ
  per bin (RVT) and 2.3 nJ (SRAM-Vt); the ASAP7 flip-flop and clock-gate clock-pin tables are conditioned on the joint state of
  D and QN, whose time-averaged probabilities over the clocked cycles do not reproduce the per-edge correlation of the round-7
  active window. Not pursued further; the kit's P_avg is set by its leakage, whose own state dependence (-20 % against the
  round-7 idle run) is described above.
- **sky130 1.28 V core (-9.3 % on P_total, -11 % on E_dyn).** The round-6 reference was measured on the first 200 bins
  annotated; the real-time run covers 5,000 bins. On the 1.8 V pruned core the first 200 bins carry 12.6 % more dynamic energy
  per bin than the 5,000-bin average (3.153 against 2.801 nJ in the round-7 chain). Scaled to the same window the two 1.28 V
  values agree within 0.1 % (1.271 against 1.272 nJ). Leakage 0.0731 against 0.0732 uW.
- **GF180 at 3.3 V and 1.8 V (+6 % on P_total, +8.9 % on E_dyn).** The round-6 re-evaluations used the 500-bin zero-delay
  window; the new runs are annotated over 5,000 bins. On the same core at 5 V the annotated 5,000-bin value exceeds the zero-delay
  500-bin value by 8.2 % (46.32 against 42.82 nJ); with that factor the 3.3 V and 1.8 V results agree within 0.5 %.
- **RISC-V SoC with the -O2 firmware does not meet real time.** The hand-tuned firmware decodes a bin in 1.09 ms on average
  (maximum 2.40 ms) and passed the 100-bin real-time run (562.7 uW; 574.5 uW with the macro state correction; round-7 sum
  573.8 uW, +0.1 %). The -O2 firmware needs 2.13 ms on average and up to 5.56 ms per bin: in 10 of the 100 bins the SoC is not
  asleep when the next tick is due (`RT OVERRUN` in `sim/build_riscv_rt_5m_o2_rt100/vvp.log`), the following bins start late and
  the testbench reports FAIL. The decode result is still correct (all 100 bins match, `tohost = 1`), and its power over the same
  0.4 s window was evaluated anyway (`sim/rt_finish_soc.sh`): the appendix row carries it with the flag `real-time: 10 overruns`.
- **SoC decap-free fill.** The SoC is built in `sky130_fd_sc_ms`; its 34,539 `decap_4` cells were replaced by fill cells (2,138
  decaps remain where no filler fits), the logic is unchanged, but the ms decap cells have no leakage in the liberty (the hd decap
  cells do), so P_leakage is the same 4.674 uW for both fills and the row's decap-free columns repeat the default values.
- **Hardenings.** `bmi_snn_hwg` accepted at 30 % (09:49; the 40 % detailed routing stalled at 42 violations and was stopped
  after 10 h), `bmi_snn_g16` at 50 % (09:49; 60 % stalled at 210 violations), `bmi_snn_min32g` 50 %, `bmi_snn_g32` 40 %.
  `bmi_snn_scmemg` failed hold by 55 ps at 30 % with the 0.5 ns repair margin (two earlier 30 % attempts died: OOM at 00:27,
  OpenROAD segfault at 01:26); rerunning at 30 % with a 0.8 ns margin (u30h). `bmi_snn_lmem2g` failed hold at 30 % and 20 %
  (-4.5 and -1.0 ns, 5,126 register-to-register endpoints): the write-clock gate drives a 1.1 pF net with an 8.6 ns slew to a
  root buffer placed far away, so the write-clock domain has a 16 ns latency against 3.4 ns for the core clock at the slow
  corner; rerunning at 30 % with CTS buffers every 150 um on clock wires longer than 300 um, a 1.0 ns hold margin and the full
  hold-buffer budget (u30h2).

- **Cell output-port variables left constant by the simulator (found 14:30 on the 12-bit latch core).** In the annotated
  50-bin run of `bmi_snn_lmin2` the toggle file holds, for 657 of the 67,126 cell output pins, a port variable with zero
  transitions (constant 1 or 0 over the whole window) while the net driven by that pin toggles normally (96 of the 158 buffers of
  the write-clock tree among them). Icarus leaves these port variables unchanged under annotated interconnect delays; the
  zero-delay run of the same netlist and every other annotated run of this round (SRAM core, hardwired cores, grid, kits,
  register-file and 20-bit latch cores) show no such pin. The activity converter wrote the cell-pin commands after the net
  commands, so for these 657 driver pins the constant port variable overrode the net's measured activity: the clock-tree leaves
  of the write and membrane clocks and their flip-flop clock pins were charged with zero activity, 0.53 nJ per bin too little
  (E_dyn 3.84 instead of about 4.4 nJ). The round-7 run of the same netlist (`bmi_snn_lmin2_5m_sdf_w50`) has the same artefact
  on 367 pins, so its reference value (4.28 nJ) is low as well. Fix: `power/toggles_to_activity.py` now emits the net commands
  after the pin commands (a net's measured activity is authoritative for its driver pin); `sw/pin_net_consistency10.py` reports
  the inconsistent pins of a toggle file. Among the finished runs only the lmin2 annotated run was affected; it was re-evaluated
  with the fix (its consistency row therefore shows a positive deviation, +2.5 % on E_dyn, against the low round-7 value). The
  annotated run of the gated 20-bit latch core (`bmi_snn_lmem2g`, finished 14:27) carries the same artefact on 2,913 of its
  83,497 output pins and was evaluated with the fixed converter from the start; the gated register-file annotated run
  (finished 16:40, 382 min) has none of its 141,340 output pins affected.

## Generated tables (sw/runlog_tables10.py, sw/collect_round10.py)

### Consistency check: round-7 sum against the real-time P_total (every existing netlist)

| row | run | window | P_total new (uW) | round-7 sum (uW) | dev. | P_leak new / old (uW) | E_dyn new / old (nJ) | dev. E_dyn | with state corr.: P_total (uW, dev.) | E_dyn (nJ, dev.) | dev. E_dyn after window/model adj. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| soc_tuned | sdf | 100 | 562.7 | 573.8 | -1.9 % | 4.674 / -- | 2,232 / -- | -- % | 574.5 (+0.1 %) | 2,279 (-- %) | -- % |
| top_dense | sdf dense | 500 | 88.72 | 94.22 | -5.8 % | 2.436 / 2.437 | 345.1 / 367.1 | -6.0 % | 93.67 (-0.6 %) | 364.9 (-0.6 %) | -- % |
| top_dense | func dense | 2000 | 76.60 | 81.71 | -6.3 % | 2.436 / 2.437 | 296.6 / 317.1 | -6.5 % | 81.55 (-0.2 %) | 316.4 (-0.2 %) | -- % |
| top_dense | func dense | 100 | 76.39 | 81.71 | -6.5 % | 2.436 / 2.437 | 295.8 / 317.1 | -6.7 % | 81.34 (-0.5 %) | 315.6 (-0.5 %) | -- % |
| top_dense | sdf dense | 40 | 88.90 | 94.22 | -5.7 % | 2.436 / 2.437 | 345.8 / 367.1 | -5.8 % | 93.85 (-0.4 %) | 365.6 (-0.4 %) | -- % |
| top_event | sdf | 2000 | 12.07 | 12.46 | -3.1 % | 2.436 / 2.437 | 38.55 / 40.08 | -3.8 % | 12.44 (-0.2 %) | 40.01 (-0.2 %) | -- % |
| topg_dense | sdf dense | 500 | 75.53 | 81.46 | -7.3 % | 2.580 / 2.584 | 291.8 / 315.5 | -7.5 % | 80.49 (-1.2 %) | 311.6 (-1.2 %) | -- % |
| topg_dense | func dense | 2000 | 60.38 | 65.24 | -7.5 % | 2.580 / 2.584 | 231.2 / 250.6 | -7.8 % | 65.33 (+0.1 %) | 251.0 (+0.2 %) | -- % |
| topg_dense | func dense | 100 | 60.01 | 65.24 | -8.0 % | 2.580 / 2.584 | 229.7 / 250.6 | -8.3 % | 64.96 (-0.4 %) | 249.5 (-0.4 %) | -- % |
| topg_dense | sdf dense | 40 | 76.23 | 81.46 | -6.4 % | 2.580 / 2.584 | 294.6 / 315.5 | -6.6 % | 81.18 (-0.3 %) | 314.4 (-0.4 %) | -- % |
| topg_event | sdf | 2000 | 9.734 | 10.13 | -3.9 % | 2.580 / 2.584 | 28.62 / 30.17 | -5.2 % | 10.10 (-0.3 %) | 30.07 (-0.3 %) | -- % |
| scmem | sdf | 50 | 6.817 | 6.816 | +0.0 % | 4.856 / 4.861 | 7.844 / 7.818 | +0.3 % | 6.817 (+0.0 %) | 7.845 (+0.3 %) | -- % |
| scmem | func | 5000 | 7.271 | 7.247 | +0.3 % | 4.858 / 4.861 | 9.651 / 9.543 | +1.1 % | -- (-- %) | -- (-- %) | -- % |
| scmemg | sdf | 50 | 6.072 | -- | -- % | 4.818 / -- | 5.014 / -- | -- % | 6.072 (-- %) | 5.016 (-- %) | -- % |
| scmemg | func | 5000 | 6.375 | -- | -- % | 4.819 / -- | 6.224 / -- | -- % | 6.375 (-- %) | 6.225 (-- %) | -- % |
| lmem2 | sdf | 50 | 5.072 | 5.037 | +0.7 % | 2.948 / 2.954 | 8.496 / 8.334 | +1.9 % | 5.073 (+0.7 %) | 8.497 (+2.0 %) | -- % |
| lmem2 | func | 5000 | 5.532 | 5.508 | +0.4 % | 2.948 / 2.954 | 10.34 / 10.22 | +1.2 % | -- (-- %) | -- (-- %) | -- % |
| lmem2g | sdf | 50 | 4.219 | -- | -- % | 2.921 / -- | 5.193 / -- | -- % | 4.219 (-- %) | 5.194 (-- %) | -- % |
| lmem2g | func | 5000 | 4.542 | -- | -- % | 2.920 / -- | 6.484 / -- | -- % | 4.542 (-- %) | 6.485 (-- %) | -- % |
| lmin2 | sdf | 50 | 5.477 | 5.451 | +0.5 % | 4.381 / 4.382 | 4.385 / 4.277 | +2.5 % | 5.477 (+0.5 %) | 4.385 (+2.5 %) | -- % |
| lmin2 | func | 5000 | 5.806 | 5.811 | -0.1 % | 4.381 / 4.382 | 5.699 / 5.716 | -0.3 % | -- (-- %) | -- (-- %) | -- % |
| hw | sdf | 5000 | 2.689 | 2.672 | +0.6 % | 0.4158 / 0.4174 | 9.092 / 9.019 | +0.8 % | -- (-- %) | -- (-- %) | -- % |
| hwg | sdf | 5000 | 2.146 | -- | -- % | 0.5842 / -- | 6.248 / -- | -- % | 2.146 (-- %) | 6.246 (-- %) | -- % |
| min | sdf | 5000 | 2.443 | 2.428 | +0.6 % | 0.3438 / 0.3451 | 8.399 / 8.333 | +0.8 % | -- (-- %) | -- (-- %) | -- % |
| ming | sdf | 5000 | 1.934 | 1.935 | -0.1 % | 0.4691 / 0.4708 | 5.859 / 5.858 | +0.0 % | -- (-- %) | -- (-- %) | -- % |
| m12 | sdf | 5000 | 1.872 | 1.871 | +0.0 % | 0.3620 / 0.3618 | 6.038 / 6.035 | +0.1 % | -- (-- %) | -- (-- %) | -- % |
| sp | sdf | 5000 | 0.9455 | 0.9437 | +0.2 % | 0.2438 / 0.2432 | 2.807 / 2.802 | +0.2 % | -- (-- %) | -- (-- %) | -- % |
| min32 | sdf | 5000 | 1.078 | 1.071 | +0.6 % | 0.1441 / 0.1442 | 3.735 / 3.709 | +0.7 % | -- (-- %) | -- (-- %) | -- % |
| min32g | sdf | 5000 | 0.7826 | -- | -- % | 0.1376 / -- | 2.580 / -- | -- % | -- (-- %) | -- (-- %) | -- % |
| g32 | sdf | 5000 | 0.7492 | -- | -- % | 0.1463 / -- | 2.412 / -- | -- % | -- (-- %) | -- (-- %) | -- % |
| g32p50 | sdf | 5000 | 0.5970 | 0.5960 | +0.2 % | 0.1081 / 0.1081 | 1.956 / 1.952 | +0.2 % | -- (-- %) | -- (-- %) | -- % |
| min16 | sdf | 5000 | 0.5259 | 0.5223 | +0.7 % | 0.06395 / 0.06408 | 1.848 / 1.833 | +0.8 % | -- (-- %) | -- (-- %) | -- % |
| g16 | sdf | 5000 | 0.3814 | -- | -- % | 0.06238 / -- | 1.276 / -- | -- % | 0.3815 (-- %) | 1.277 (-- %) | -- % |
| fe | sdf_vcd | 500 | 0.7004 | 0.7004 | -0.0 % | 0.01413 / -- | 2.745 / -- | -- % | -- (-- %) | -- (-- %) | -- % |
| sky130 |  |  | 0.9455 | 0.9437 | +0.2 % | 0.2438 / 0.2435 | 2.807 / 2.801 | +0.2 % | -- (-- %) | -- (-- %) | +0.2 % |
| sky130_lv |  |  | 0.3911 | 0.4310 | -9.3 % | 0.07305 / 0.07316 | 1.272 / 1.431 | -11.1 % | -- (-- %) | -- (-- %) | +0.1 % |
| sky130_nodecap |  |  | 0.7843 | 0.7826 | +0.2 % | 0.08268 / 0.08234 | 2.807 / 2.801 | +0.2 % | -- (-- %) | -- (-- %) | +0.2 % |
| gf180 |  |  | 15.78 | 15.71 | +0.5 % | 4.121 / 4.129 | 46.64 / 46.32 | +0.7 % | 15.73 (+0.2 %) | 46.45 (+0.3 %) | +0.3 % |
| gf180_1v8 |  |  | 1.818 | 1.713 | +6.1 % | 0.5318 / 0.5326 | 5.143 / 4.723 | +8.9 % | 1.812 (+5.8 %) | 5.123 (+8.5 %) | +0.2 % |
| gf180_3v3 |  |  | 6.507 | 6.124 | +6.2 % | 1.789 / 1.792 | 18.87 / 17.33 | +8.9 % | 6.488 (+5.9 %) | 18.80 (+8.5 %) | +0.3 % |
| ihp |  |  | 60.12 | 60.16 | -0.1 % | 59.55 / 59.59 | 2.279 / 2.269 | +0.5 % | 60.12 (-0.1 %) | 2.283 (+0.6 %) | +0.6 % |
| ihp_nodecap |  |  | 4.252 | 4.297 | -1.1 % | 3.682 / 3.730 | 2.279 / 2.269 | +0.5 % | -- (-- %) | -- (-- %) | +0.5 % |
| nangate45 |  |  | 762.5 | 765.1 | -0.3 % | 762.4 / 765.0 | 0.4061 / 0.4055 | +0.1 % | 762.5 (-0.3 %) | 0.3959 (-2.4 %) | -2.4 % |
| asap7 |  |  | 2.665 | 3.325 | -19.9 % | 2.643 / 3.305 | 0.08761 / 0.08222 | +6.6 % | 2.665 (-19.9 %) | 0.08680 (+5.6 %) | +5.6 % |
| asap7sram |  |  | 0.6030 | 0.7394 | -18.4 % | 0.5825 / 0.7195 | 0.08204 / 0.07969 | +2.9 % | 0.6029 (-18.5 %) | 0.08130 (+2.0 %) | +2.0 % |

### Hardening records

| core | spec | run tag | utilization target | cells | area (mm^2) | setup slack worst corner (ns) | hold slack worst corner (ns) | route DRC | policy history |
|---|---|---|---|---|---|---|---|---|---|
| bmi_snn_top | round 5-7 netlist | bmi_snn_top_5m_u60 | 60 % | 13479 | 0.6428 | 117.1 | 0.1106 | 0 | 60 % accepted |
| bmi_snn_topg | E1: SRAM core, gated (round 7 netlist; dense mode = simulation only) | bmi_snn_topg_5m_u40 | 40 % | 20914 | 0.6903 | 118.0 | 0.5570 | 0 | 60 % rejected (runtime=14min drc=NA pass=0 die=990x900); 50 % rejected (runtime=6min drc=NA pass=0 die=1060x900); 40 % accepted |
| bmi_snn_scmem | round 5-7 netlist | bmi_snn_scmem_5m_u30 | 30 % | 301258 | 2.680 | 77.37 | 0.5146 | 0 | 40 % rejected (runtime=250min drc=NA pass=0 watchdog="drt 93733 violations ); 30 % accepted |
| bmi_snn_scmemg | E2: register-file memory 20/24, gated | bmi_snn_scmemg_5m_u30h | 30 % | 304003 | 2.721 | 76.32 | 0.2927 | 0 | 30 % rejected (runtime=65min drc=NA pass=0); 30 % rejected (runtime=55min drc=NA pass=0); 30 % rejected (runtime=50min drc=0 pass=0); 30 % accepted |
| bmi_snn_lmem2 | round 5-7 netlist | bmi_snn_lmem2_5m_u30h | 30 % | 208689 | 1.816 | 0 | 0.9875 | 0 | 30 % rejected (runtime=310min drc=NA pass=0 watchdog="drt 125966 violations); 20 % rejected (runtime=1min drc=NA pass=0 killed="aborted at start: the 30 ); 30 % accepted |
| bmi_snn_lmem2g | E3: latch memory 20/24, gated | bmi_snn_lmem2g_5m_u30h2 | 30 % | 221063 | 1.898 | 0 | 0.3611 | 0 | 30 % rejected (runtime=230min drc=0 pass=0); 20 % rejected (runtime=85min drc=0 pass=0); 30 % accepted |
| bmi_snn_lmin2 | round 5-7 netlist | bmi_snn_lmin2_5m_u20h | 20 % | 227127 | 1.840 | 0 | 0.4223 | 0 | 60 % rejected (runtime=470min drc=NA pass=0 killed="detailed routing: no it); 30 % rejected (runtime=665min drc=NA pass=0 watchdog="drt 145347 violations); 20 % rejected (runtime=265min drc=0 pass=0); 20 % rejected (runtime=175min drc=NA pass=0 watchdog="drt 93343 violations ); 20 % accepted |
| bmi_snn_hw | round 5-7 netlist | bmi_snn_hw_5m_u40 | 40 % | 40562 | 0.2861 | 116.8 | 0.3157 | 0 | 60 % rejected (runtime=165min drc=NA pass=0 watchdog="drt 121933 violations); 50 % rejected (runtime=140min drc=NA pass=0 watchdog="drt 23294 violations ); 40 % accepted |
| bmi_snn_hwg | E4: hardwired dense 20/24, gated | bmi_snn_hwg_5m_u30 | 30 % | 42800 | 0.2839 | 118.1 | 0.07854 | 0 | 40 % rejected (runtime=615min drc=NA pass=0); 30 % accepted |
| bmi_snn_min | round 5-7 netlist | bmi_snn_min_5m_u40 | 40 % | 34319 | 0.2446 | 118.1 | 0.1387 | 0 | 60 % rejected (runtime=225min drc=NA pass=0 watchdog="drt 290,447 violation); 50 % rejected (runtime=100min drc=NA pass=0 watchdog="drt 77045 violations ); 40 % accepted |
| bmi_snn_ming | round 5-7 netlist | bmi_snn_ming_5m_u30 | 30 % | 35875 | 0.2465 | 118.0 | 0.1641 | 0 | 60 % rejected (runtime=470min drc=NA pass=0 killed="detailed routing hopele); 40 % rejected (runtime=175min drc=NA pass=0 watchdog="drt 4211 violations a); 30 % accepted |
| bmi_snn_m12 | round 5-7 netlist | bmi_snn_m12_5m_u30h | 30 % | 32603 | 0.2396 | 118.1 | 0.2024 | 0 | 60 % rejected (runtime=9min drc=NA pass=0); 50 % rejected (runtime=12min drc=NA pass=0); 40 % rejected (runtime=500min drc=NA pass=0 killed="GRT-0097 no global rout); 40 % rejected (runtime=215min drc=NA pass=0 watchdog="drt no completed iter); 30 % rejected (runtime=80min drc=0 pass=0); 20 % rejected (runtime=10min drc=NA pass=0 killed="hold failure at 30 % is ); 30 % accepted |
| bmi_snn_sp | round 5-7 netlist | bmi_snn_sp_5m_u40 | 40 % | 24546 | 0.1761 | 118.1 | 0.1310 | 0 | 60 % rejected (runtime=5min drc=NA pass=0); 50 % rejected (runtime=500min drc=NA pass=0 killed="detailed routing hopele); 40 % accepted |
| bmi_snn_min32 | round 5-7 netlist | bmi_snn_min32_5m_u50 | 50 % | 16744 | 0.1194 | 118.2 | 0.1119 | 0 | 60 % rejected (runtime=470min drc=NA pass=0 killed="detailed routing hopele); 50 % accepted |
| bmi_snn_min32g | E5: H = 32 dense 16/16, gated | bmi_snn_min32g_5m_u50 | 50 % | 16883 | 0.1212 | 117.4 | 0.1194 | 0 | 50 % accepted |
| bmi_snn_g32 | E5: H = 32 dense 12/14, gated (grid point) | bmi_snn_g32_5m_u40 | 40 % | 14857 | 0.1066 | 117.4 | 0.2213 | 0 | 50 % rejected (runtime=75min drc=NA pass=0 watchdog="drt 9712 violations af); 40 % accepted |
| bmi_snn_g32p50 | round 5-7 netlist | bmi_snn_g32p50_5m_u50 | 50 % | 13775 | 0.1010 | 117.2 | 0.1968 | 0 | 60 % rejected (runtime=315min drc=NA pass=0 killed="detailed routing hopele); 50 % accepted |
| bmi_snn_min16 | round 5-7 netlist | bmi_snn_min16_5m_u60 | 60 % | 9150 | 0.06549 | 117.2 | 0.1136 | 0 | 60 % accepted; 60 % accepted |
| bmi_snn_g16 | E5: H = 16 dense 12/14, gated (grid point) | bmi_snn_g16_5m_u50 | 50 % | 8109 | 0.05844 | 116.6 | 0.2927 | 0 | 60 % rejected (runtime=535min drc=NA pass=0); 50 % accepted |
| bmi_snn_g128 | round 5-7 netlist | bmi_snn_g128_5m_u20h2 | 20 % | 78735 | 0.5671 | 117.6 | 0.4809 | 0 | 50 % rejected (runtime=215min drc=NA pass=0 killed="manual: drt 769k violat); 30 % rejected (runtime=120min drc=NA pass=0 killed="manual: 190k violations); 30 % rejected (runtime=195min drc=NA pass=0 watchdog="manual: 190k -> 145k ); 20 % rejected (runtime=120min drc=0 pass=0); 20 % rejected (runtime=115min drc=0 pass=0); 20 % accepted |
| bmi_snn_g128p25 | round 5-7 netlist | bmi_snn_g128p25_5m_u30 | 30 % | 51113 | 0.3562 | 117.5 | 0.09279 | 0 | 50 % rejected (runtime=165min drc=NA pass=0 watchdog="drt 44899 violations ); 40 % rejected (runtime=150min drc=NA pass=0 watchdog="drt 20089 violations ); 30 % accepted |
| bmi_snn_g128p125 | round 5-7 netlist | bmi_snn_g128p125_5m_u50 | 50 % | 40320 | 0.2924 | 117.9 | 0.09768 | 0 | 50 % accepted |
| bmi_snn_g64p50 | round 5-7 netlist | bmi_snn_g64p50_5m_u30 | 30 % | 29067 | 0.2041 | 117.3 | 0.1520 | 0 | 50 % rejected (runtime=80min drc=NA pass=0 watchdog="drt 87987 violations a); 40 % rejected (runtime=220min drc=NA pass=0 watchdog="drt no completed iter); 30 % accepted |
| bmi_snn_g64p125 | round 5-7 netlist | bmi_snn_g64p125_5m_u50 | 50 % | 19914 | 0.1415 | 118.1 | 0.3135 | 0 | 50 % accepted |
| bmi_snn_g48 | round 5-7 netlist | bmi_snn_g48_5m_u30h | 30 % | 25150 | 0.1833 | 118.1 | 0.4933 | 0 | 60 % rejected (runtime=146min drc=NA pass=0 killed="drt 163964 violations a); 40 % rejected (runtime=30min drc=0 pass=0); 30 % rejected (runtime=2min drc=NA pass=0 killed="stopped: 40 % failed hold); 40 % rejected (runtime=35min drc=NA pass=0 watchdog="drt 56536 violations a); 30 % accepted |
| bmi_snn_g48p50 | round 5-7 netlist | bmi_snn_g48p50_5m_u40 | 40 % | 20614 | 0.1489 | 117.1 | 0.1597 | 0 | 60 % rejected (runtime=146min drc=NA pass=0 killed="drt 132137 violations a); 40 % accepted |
| bmi_snn_g48p25 | round 5-7 netlist | bmi_snn_g48p25_5m_u50 | 50 % | 17777 | 0.1303 | 118.0 | 0.07376 | 0 | 60 % rejected (runtime=90min drc=NA pass=0 watchdog="drt 68586 violations a); 50 % accepted |
| bmi_snn_g32p25 | round 5-7 netlist | bmi_snn_g32p25_5m_u50 | 50 % | 12526 | 0.09164 | 117.9 | 0.2545 | 0 | 50 % accepted |
| bmi_snn_g32p125 | round 5-7 netlist | bmi_snn_g32p125_5m_u60 | 60 % | 10274 | 0.07396 | 118.2 | 0.3104 | 0 | 60 % accepted |
| bmi_snn_g16p50 | round 5-7 netlist | bmi_snn_g16p50_5m_u60 | 60 % | 7359 | 0.05424 | 116.1 | 0.3175 | 0 | 60 % accepted |

### Decap-free refill records (E10)

| design | run | route DRC (original / refill) | cells (default / decap-free) | decap cells | P_leak default (uW) | P_leak decap-free (uW) | leakage by class default: logic / fill / decap / tap (uW) | decap-free: logic / fill / decap / tap (uW) | P_dyn default / decap-free (uW) | E_bin default / decap-free (nJ) |
|---|---|---|---|---|---|---|---|---|---|---|
| soc_tuned | sdf w100 | 0 / 0 | 63890 / 63892 | 34539 -> 2138 | 4.674 | 4.674 | 4.674 / 0 / 0 / 0 | 4.674 / 0 / 0 / 0 | 558.1 / 558.1 | 2,251 / 2,251 |
| soc_o2 | sdf w100 | 0 / 0 | 63890 / 63892 | 34539 -> 2138 | 4.674 | 4.674 | 4.674 / 0 / 0 / 0 | 4.674 / 0 / 0 / 0 | 1,032 / 1,032 | 4,145 / 4,145 |
| bmi_snn_top | sdf dense w500 | 0 / 0 | 13479 / 13480 | 14579 -> 1222 | 2.436 | 2.393 | 2.389 / 0 / 0.04724 / 0 | 2.389 / 0 / 0.003959 / 0 | 86.28 / 86.28 | 354.9 / 354.7 |
| bmi_snn_top | func dense w2000 | 0 / 0 | 13479 / 13480 | 14579 -> 1222 | 2.436 | 2.393 | 2.389 / 0 / 0.04724 / 0 | 2.389 / 0 / 0.003959 / 0 | 74.16 / 74.16 | 306.4 / 306.2 |
| bmi_snn_top | func dense w100 | 0 / 0 | 13479 / 13480 | -- -> 1222 | 2.436 | 2.393 | -- / -- / -- / -- | 2.389 / 0 / 0.003959 / 0 | 73.95 / 73.95 | 305.6 / 305.4 |
| bmi_snn_top | sdf dense w40 | 0 / 0 | 13479 / 13480 | 14579 -> 1222 | 2.436 | 2.393 | 2.389 / 0 / 0.04724 / 0 | 2.389 / 0 / 0.003959 / 0 | 86.46 / 86.46 | 355.6 / 355.4 |
| bmi_snn_top | sdf w2000 | 0 / 0 | 13479 / 13480 | 14579 -> 1222 | 2.436 | 2.393 | 2.389 / 0 / 0.04724 / 0 | 2.389 / 0 / 0.003959 / 0 | 9.638 / 9.638 | 48.30 / 48.12 |
| bmi_snn_topg | sdf dense w500 | 0 / 0 | 20914 / 20915 | 56089 -> 1222 | 2.580 | 2.402 | 2.398 / 0 / 0.1817 / 0 | 2.398 / 0 / 0.003959 / 0 | 72.95 / 72.95 | 302.1 / 301.4 |
| bmi_snn_topg | func dense w2000 | 0 / 0 | 20914 / 20915 | 56089 -> 1222 | 2.580 | 2.402 | 2.398 / 0 / 0.1817 / 0 | 2.398 / 0 / 0.003959 / 0 | 57.80 / 57.80 | 241.5 / 240.8 |
| bmi_snn_topg | func dense w100 | 0 / 0 | 20914 / 20915 | 56089 -> 1222 | 2.580 | 2.402 | 2.398 / 0 / 0.1817 / 0 | 2.398 / 0 / 0.003959 / 0 | 57.43 / 57.43 | 240.0 / 239.3 |
| bmi_snn_topg | sdf dense w40 | 0 / 0 | 20914 / 20915 | 56089 -> 1222 | 2.580 | 2.403 | 2.399 / 0 / 0.1817 / 0 | 2.399 / 0 / 0.003959 / 0 | 73.65 / 73.65 | 304.9 / 304.2 |
| bmi_snn_topg | sdf w2000 | 0 / 0 | 20914 / 20915 | 56089 -> 1222 | 2.580 | 2.402 | 2.398 / 0 / 0.1817 / 0 | 2.398 / 0 / 0.003959 / 0 | 7.154 / 7.154 | 38.94 / 38.22 |
| bmi_snn_scmem | sdf w50 | 0 / 0 | 301258 / 301258 | 1183383 -> 1994 | 4.856 | 1.073 | 1.057 / 0 / 3.799 / 0 | 1.067 / 0 / 0.006462 / 0 | 1.961 / 1.961 | 27.27 / 12.14 |
| bmi_snn_scmem | func w5000 | 0 / 0 | 301258 / 301258 | 1183383 -> 1994 | 4.858 | 1.076 | 1.059 / 0 / 3.799 / 0 | 1.069 / 0 / 0.006461 / 0 | 2.413 / 2.413 | 29.09 / 13.95 |
| bmi_snn_scmemg | sdf w50 | 0 / 0 | 304003 / 304003 | 1164603 -> 1990 | 4.818 | 1.095 | 1.079 / 0 / 3.739 / 0 | 1.089 / 0 / 0.006448 / 0 | 1.254 / 1.254 | 24.29 / 9.396 |
| bmi_snn_scmemg | func w5000 | 0 / 0 | 304003 / 304003 | 1164603 -> 1990 | 4.819 | 1.096 | 1.080 / 0 / 3.739 / 0 | 1.090 / 0 / 0.006448 / 0 | 1.556 / 1.556 | 25.50 / 10.61 |
| bmi_snn_lmem2 | sdf w50 | 0 / 0 | 208689 / 208689 | 654936 -> 1548 | 2.948 | 0.8528 | 0.8417 / 0 / 2.107 / 0 | 0.8478 / 0 / 0.005015 / 0 | 2.124 / 2.124 | 20.29 / 11.91 |
| bmi_snn_lmem2 | func w5000 | 0 / 0 | 208689 / 208689 | 654936 -> 1548 | 2.948 | 0.8526 | 0.8415 / 0 / 2.107 / 0 | 0.8476 / 0 / 0.005016 / 0 | 2.584 / 2.584 | 22.13 / 13.75 |
| bmi_snn_lmem2g | sdf w50 | 0 / 0 | 221063 / 221063 | 626867 -> 1544 | 2.921 | 0.9149 | 0.9034 / 0 / 2.017 / 0 | 0.9099 / 0 / 0.005004 / 0 | 1.298 / 1.298 | 16.88 / 8.852 |
| bmi_snn_lmem2g | func w5000 | 0 / 0 | 221063 / 221063 | 626867 -> 1544 | 2.920 | 0.9147 | 0.9033 / 0 / 2.017 / 0 | 0.9097 / 0 / 0.005004 / 0 | 1.621 / 1.621 | 18.17 / 10.14 |
| bmi_snn_lmin2 | sdf w50 | 0 / 0 | 227127 / 227127 | 1105606 -> 1828 | 4.381 | 0.8516 | 0.8368 / 0 / 3.544 / 0 | 0.8457 / 0 / 0.005922 / 0 | 1.096 / 1.096 | 21.91 / 7.791 |
| bmi_snn_lmin2 | func w5000 | 0 / 0 | 227127 / 227127 | 1105606 -> 1828 | 4.381 | 0.8517 | 0.8369 / 0 / 3.544 / 0 | 0.8458 / 0 / 0.005922 / 0 | 1.425 / 1.425 | 23.22 / 9.106 |
| bmi_snn_hw | sdf w5000 | 0 / 0 | 40562 / 40562 | 91236 -> 594 | 0.4158 | 0.1221 | 0.1202 / 0 / 0.2956 / 0 | 0.1202 / 0 / 0.001924 / 0 | 2.273 / 2.273 | 10.76 / 9.581 |
| bmi_snn_hwg | sdf w5000 | 0 / 0 | 42800 / 42800 | 142504 -> 678 | 0.5842 | 0.1246 | 0.1224 / 0 / 0.4617 / 0 | 0.1224 / 0 / 0.002197 / 0 | 1.562 / 1.562 | 8.585 / 6.747 |
| bmi_snn_min | sdf w5000 | 0 / 0 | 34319 / 34319 | 73916 -> 542 | 0.3438 | 0.1060 | 0.1043 / 0 / 0.2395 / 0 | 0.1043 / 0 / 0.001756 / 0 | 2.100 / 2.100 | 9.774 / 8.823 |
| bmi_snn_ming | sdf w5000 | 0 / 0 | 35875 / 35875 | 112185 -> 612 | 0.4691 | 0.1075 | 0.1056 / 0 / 0.3635 / 0 | 0.1056 / 0 / 0.001983 / 0 | 1.465 / 1.465 | 7.735 / 6.289 |
| bmi_snn_m12 | sdf w5000 | 0 / 0 | 32603 / 32603 | 79912 -> 550 | 0.3620 | 0.1048 | 0.1031 / 0 / 0.2589 / 0 | 0.1030 / 0 / 0.001782 / 0 | 1.510 / 1.510 | 7.486 / 6.458 |
| bmi_snn_sp | sdf w5000 | 0 / 0 | 24546 / 24546 | 50180 -> 454 | 0.2438 | 0.08268 | 0.08121 / 0 / 0.1626 / 0 | 0.08121 / 0 / 0.001471 / 0 | 0.7017 / 0.7017 | 3.782 / 3.137 |
| bmi_snn_min32 | sdf w5000 | 0 / 0 | 16744 / 16744 | 28070 -> 356 | 0.1441 | 0.05427 | 0.05312 / 0 / 0.09095 / 0 | 0.05312 / 0 / 0.001153 / 0 | 0.9339 / 0.9339 | 4.312 / 3.952 |
| bmi_snn_min32g | sdf w5000 | 0 / 0 | 16883 / 16883 | 25662 -> 350 | 0.1376 | 0.05558 | 0.05445 / 0 / 0.08315 / 0 | 0.05445 / 0 / 0.001134 / 0 | 0.6450 / 0.6450 | 3.131 / 2.802 |
| bmi_snn_g32 | sdf w5000 | 0 / 0 | 14857 / 14857 | 30455 -> 352 | 0.1463 | 0.04876 | 0.04762 / 0 / 0.09868 / 0 | 0.04762 / 0 / 0.001140 / 0 | 0.6029 / 0.6029 | 2.997 / 2.607 |
| bmi_snn_g32p50 | sdf w5000 | 0 / 0 | 13775 / 13775 | 19126 -> 312 | 0.1081 | 0.04710 | 0.04609 / 0 / 0.06197 / 0 | 0.04609 / 0 / 0.001011 / 0 | 0.4890 / 0.4890 | 2.388 / 2.144 |
| bmi_snn_min16 | sdf w5000 | 0 / 0 | 9150 / 9150 | 10506 -> 244 | 0.06395 | 0.03070 | 0.02991 / 0 / 0.03404 / 0 | 0.02991 / 0 / 0.0007906 / 0 | 0.4619 / 0.4619 | 2.103 / 1.970 |
| bmi_snn_g16 | sdf w5000 | 0 / 0 | 8109 / 8109 | 11246 -> 238 | 0.06238 | 0.02671 | 0.02594 / 0 / 0.03644 / 0 | 0.02594 / 0 / 0.0007711 / 0 | 0.3190 / 0.3190 | 1.526 / 1.383 |

### Wall-clock of the annotated runs

| run | model | bins | cells | clock cycles in window | simulation wall-clock (min) | pins annotated |
|---|---|---|---|---|---|---|
| riscv_rt_5m_tuned_rt100 | sdf | 100 | 63890 | 544946 | 273 | 99.98 % |
| riscv_rt_5m_o2_rt100 | sdf | 100 | 63890 | 1062864 | 380 | 99.98 % |
| rt_bmi_snn_top_5m_sdf_md1_w500_indy_20160630_01 | sdf | 500 | 13479 | 822302 | 349 | 99.99 % |
| rt_bmi_snn_top_5m_func_md1_w2000_indy_20160630_01 | func | 2000 | 13479 | 3287345 | 197 | 99.99 % |
| rt_bmi_snn_top_5m_func_md1_w100_indy_20160630_01 | func | 100 | 13479 | 164185 | 11.1 | 99.99 % |
| rt_bmi_snn_top_5m_sdf_md1_w40_indy_20160630_01 | sdf | 40 | 13479 | 65464 | 48.6 | 99.99 % |
| rt_bmi_snn_top_5m_sdf_md0_w2000_indy_20160630_01 | sdf | 2000 | 13479 | 370955 | 226 | 99.99 % |
| rt_bmi_snn_topg_5m_sdf_md1_w500_indy_20160630_01 | sdf | 500 | 20914 | 822302 | 439 | 99.99 % |
| rt_bmi_snn_topg_5m_func_md1_w2000_indy_20160630_01 | func | 2000 | 20914 | 3287345 | 357 | 99.99 % |
| rt_bmi_snn_topg_5m_func_md1_w100_indy_20160630_01 | func | 100 | 20914 | 164185 | 42.6 | 99.99 % |
| rt_bmi_snn_topg_5m_sdf_md1_w40_indy_20160630_01 | sdf | 40 | 20914 | 65464 | 74.5 | 99.99 % |
| rt_bmi_snn_topg_5m_sdf_md0_w2000_indy_20160630_01 | sdf | 2000 | 20914 | 370955 | 242 | 99.99 % |
| rt_bmi_snn_scmem_5m_sdf_md0_w50_indy_20160630_01 | sdf | 50 | 301258 | 1110 | 458 | 100 % |
| rt_bmi_snn_scmem_5m_func_md0_w5000_indy_20160630_01 | func | 5000 | 301258 | 132963 | 85.3 | 100 % |
| rt_bmi_snn_scmemg_5m_sdf_md0_w50_indy_20160630_01 | sdf | 50 | 304003 | 1110 | 375 | 100 % |
| rt_bmi_snn_scmemg_5m_func_md0_w5000_indy_20160630_01 | func | 5000 | 304003 | 132963 | 18.9 | 100 % |
| rt_bmi_snn_lmem2_5m_sdf_md0_w50_indy_20160630_01 | sdf | 50 | 208689 | 1162 | 276 | 100 % |
| rt_bmi_snn_lmem2_5m_func_md0_w5000_indy_20160630_01 | func | 5000 | 208689 | 139143 | 80.8 | 100 % |
| rt_bmi_snn_lmem2g_5m_sdf_md0_w50_indy_20160630_01 | sdf | 50 | 221063 | 1162 | 178 | 100 % |
| rt_bmi_snn_lmem2g_5m_func_md0_w5000_indy_20160630_01 | func | 5000 | 221063 | 139143 | 16.6 | 100 % |
| rt_bmi_snn_lmin2_5m_sdf_md0_w50_indy_20160630_01 | sdf | 50 | 227127 | 1162 | 251 | 100 % |
| rt_bmi_snn_lmin2_5m_func_md0_w5000_indy_20160630_01 | func | 5000 | 227127 | 139150 | 53.3 | 100 % |
| rt_bmi_snn_hw_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 40562 | 123107 | 208 | 100 % |
| rt_bmi_snn_hwg_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 42800 | 123107 | 54.0 | 100 % |
| rt_bmi_snn_min_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 34319 | 123107 | 185 | 100 % |
| rt_bmi_snn_ming_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 35875 | 123107 | 145 | 100 % |
| rt_bmi_snn_m12_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 32603 | 123112 | 148 | 100 % |
| rt_bmi_snn_sp_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 24546 | 122228 | 68.6 | 100 % |
| rt_bmi_snn_min32_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 16744 | 122079 | 91.8 | 100 % |
| rt_bmi_snn_min32g_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 16883 | 122079 | 69.3 | 100 % |
| rt_bmi_snn_g32_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 14857 | 122083 | 55.2 | 100 % |
| rt_bmi_snn_g32p50_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 13775 | 121808 | 42.3 | 100 % |
| rt_bmi_snn_min16_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 9150 | 120799 | 40.3 | 100 % |
| rt_bmi_snn_g16_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 8109 | 120802 | 7.55 | 100 % |
| rt_bmi_snn_sp_5m_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 24546 | 122228 | 68.6 | 100 % |
| rt_bmi_snn_sp_5m_lv_sdf_md0_w5000_indy_20160630_01 | sdf | 5000 | 32484 | 122228 | 87.2 | 100 % |
| rt_bmi_snn_sp_5m_sdf_md0_w5000_indy_20160630_01_nodecap | sdf | 5000 | 24546 | 122228 | 68.6 | 100 % |
| rt_pdk_gf180_sp_sdf_w5000 | sdf | 5000 | 18951 | 122228 | 78.0 | 100 % |
| rt_pdk_gf180_sp_sdf_w5000_tt_025C_1v80 | sdf | 5000 | 18951 | 122228 | 78.0 | 100 % |
| rt_pdk_gf180_sp_sdf_w5000_tt_025C_3v30 | sdf | 5000 | 18951 | 122228 | 78.0 | 100 % |
| rt_pdk_ihp_sp_sdf_w5000 | sdf | 5000 | 23453 | 122228 | 62.8 | 100 % |
| rt_pdk_ihp_sp_nodecap_sdf_w5000 | sdf | 5000 | 23453 | 122228 | 62.8 | 100 % |
| rt_pdk_nangate45_sp_func_w5000 | func | 5000 | 22570 | 122228 | 12.5 | 100 % |
| rt_pdk_asap7_sp_sdf_w5000 | sdf | 5000 | 19954 | 122228 | 60.1 | 100 % |
| rt_pdk_asap7sram_sp_sdf_w5000 | sdf | 5000 | 19604 | 122228 | 54.7 | 100 % |

### Headline ratios, round 7 vs round 10

| ratio | round 7 (sum of active-window energy x 250/s and leakage) | round 10 (real-time window) | round 10 with the state corrections |
|---|---|---|---|
| SoC / pruned core | 608 | 595 | 608 |
| SoC / 12-bit hardwired | 307 | 301 | 307 |
| SRAM core, event mode / pruned core | 10.7 | 10.3 | 10.7 |
| SRAM core, dense / event | 8.04 | 7.76 | 7.97 |
| register file / latch memory | -- | 1.44 | 1.44 |
| latch 20-bit / latch 12-bit | -- | 0.770 | 0.770 |
| hardwired 20-bit / 12-bit | -- | 1.15 | 1.15 |
| 12-bit dense / pruned core | 1.98 | 1.98 | 1.98 |
| H = 64 / H = 32 (12-bit, gated) | -- | 2.50 | 2.50 |
| pruned core / front end | 1.35 | 1.35 | 1.35 |

