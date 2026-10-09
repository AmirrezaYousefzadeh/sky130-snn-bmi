`timescale 1ns/1ps
// Round 10 (E6): real-time schedule of the RISC-V SoC software decoder (firmware/bmi_snn_sw*_rt.c). Derived from the skywater repo's
// simulation/tb_fw_mnist.v (same SoC instance, reset, wake pulse and PASS criterion). Schedule: reset -> power-on sleep -> wake for
// init -> firmware sleeps -> then for bin k = 0 .. N_BINS-1: at t = T_start + k x BIN_NS the external clock is restarted (it is stopped
// while the SoC sleeps), the testbench pulses `wake`, the firmware decodes one bin and writes the SLEEP register; once `sleeping` is
// back the clock is stopped again. After the last bin gpio_done rises, the firmware sleeps, the testbench wakes it for the halt.
// The waveform (DUMP_PATH) spans exactly [T_start, T_start + N_BINS x BIN_NS] (marker toggles at both ends) for the toggle-based
// power analysis over the whole real-time window.
module tb_fw_bmi_rt;
  reg reset = 1;
  reg wake = 0;
  wire halted;
  wire [31:0] tohost;
  wire gpio_done;
  wire sleeping;
  wire sram_clk_en;
`ifndef CLK_PERIOD_NS
  `define CLK_PERIOD_NS 200.0
`endif
`ifndef BIN_NS
  `define BIN_NS 4000000
`endif
`ifndef N_BINS
  `define N_BINS 100
`endif
  localparam real CLK_PERIOD_NS = `CLK_PERIOD_NS;
  localparam integer RESET_CYCLES = 64;
  localparam integer WAKE_PULSE_CYCLES = 8;
  localparam integer SLEEP_SETTLE_CYCLES = 8;   // clock edges after `sleeping` rises before the external clock is stopped
  // free-running oscillator, gated by the testbench: the SoC's clock port is idle while the core sleeps between bins
  reg osc = 0, clk_run = 1, rt_marker = 0;
  always #(CLK_PERIOD_NS / 2.0) osc = ~osc;
  wire clk = osc & clk_run;

`ifndef TIMEOUT_CYCLES
  `define TIMEOUT_CYCLES 50000000
`endif
  integer gls_cyc = 0, win_cyc = 0, awake_cyc = 0, cyc0 = 0;
  always @(posedge clk) begin
    gls_cyc = gls_cyc + 1;
    if (sram_clk_en === 1'b1) awake_cyc = awake_cyc + 1;
`ifdef GLS_PROGRESS
    if ((gls_cyc % 20000) == 0) $display("GLS_PROGRESS cycle=%0d max=%0d", gls_cyc, `TIMEOUT_CYCLES);
`endif
    if (gls_cyc > `TIMEOUT_CYCLES) begin $display("FAIL: timeout"); $fatal(1); end
  end

  sky130_vex2_soc u_soc (
    .clk(clk), .reset(reset), .wake(wake), .halted(halted), .tohost(tohost), .gpio_done(gpio_done), .sleeping(sleeping), .sram_clk_en(sram_clk_en)
  );
`ifdef GLS_RF_INIT
  `include "gls_regfile_init.vh"
`endif
`ifndef IMEM_HEX
  `define IMEM_HEX "imem.hex"
`endif
`ifndef DMEM_HEX
  `define DMEM_HEX "dmem.hex"
`endif
`ifdef DUMP_PATH
  `ifndef DUMP_LEVEL
    `define DUMP_LEVEL 1
  `endif
  `ifndef DUMP_MODULE
    `define DUMP_MODULE tb_fw_bmi_rt.u_soc
  `endif
`endif

  task automatic pulse_wake;
    integer k;
    begin
      wake = 1'b1;
      for (k = 0; k < WAKE_PULSE_CYCLES; k = k + 1) @(posedge clk);
      wake = 1'b0;
    end
  endtask
  task automatic wait_sleeping;
    integer guard;
    begin
      for (guard = 0; guard < `TIMEOUT_CYCLES; guard = guard + 1) begin
        @(posedge clk);
        if (sleeping === 1'b1) disable wait_sleeping;
      end
      $display("FAIL: timeout waiting for sleeping"); $fatal(1);
    end
  endtask

  integer i, k; reg [63:0] t_start, t_bin, t_end, t_act0, t_act_sum = 0, t_act_max = 0; integer overruns = 0, awake0 = 0;
  initial begin
`ifdef SDF_ANNOTATE
    $sdf_annotate(`SDF_ANNOTATE, u_soc);
    $display("SDF: annotated %s onto u_soc", `SDF_ANNOTATE);
`endif
    $display("CLK: period=%0g ns  reset_cycles=%0d  bin=%0d ns  bins=%0d (real time)", CLK_PERIOD_NS, RESET_CYCLES, `BIN_NS, `N_BINS);
    $readmemh(`IMEM_HEX, u_soc.u_imem.mem);
    $readmemh(`DMEM_HEX, u_soc.u_dmem.mem);
    $display("FW: loaded %s and %s", `IMEM_HEX, `DMEM_HEX);
    reset = 1'b1; wake = 1'b0;
    repeat (RESET_CYCLES) @(posedge clk);
    @(negedge clk); reset = 1'b0;
    $display("TB: reset released at t=%0t", $time);
    wait_sleeping;                       // power-on sleep
    $display("TB: power-on sleep - wake for init");
    pulse_wake;
    wait_sleeping;                       // the firmware initialized and sleeps until the first bin
    repeat (SLEEP_SETTLE_CYCLES) @(posedge clk);
    @(negedge osc); clk_run = 0;         // external clock stopped
    // measured window: starts at the next full period boundary (plus one period of margin)
    t_start = (($time / 64'd200) + 64'd2) * 64'd200;
    #(t_start - $time);
    rt_marker = ~rt_marker;
`ifdef DUMP_PATH
    $dumpfile(`DUMP_PATH); $dumpvars(`DUMP_LEVEL, `DUMP_MODULE); $dumpvars(0, rt_marker);
    $display("WAVEFORM: dumping to %s from t=%0t (window start)", `DUMP_PATH, $time);
`endif
    $display("RT: window start t=%0d ns, %0d bins of %0d ns, end t=%0d ns", t_start, `N_BINS, `BIN_NS, t_start + `N_BINS * `BIN_NS);
    cyc0 = gls_cyc; awake0 = awake_cyc;
    for (i = 0; i < `N_BINS; i = i + 1) begin
      t_bin = t_start + i * `BIN_NS;
      if ($time > t_bin) begin overruns = overruns + 1; if (overruns <= 5) $display("RT OVERRUN: bin %0d not asleep at its slot start (t=%0t > %0d)", i, $time, t_bin); end
      else #(t_bin - $time);
      @(negedge osc); clk_run = 1; t_act0 = $time;      // clock restarted; the wake synchronizer needs clock edges
      pulse_wake;                                        // wake: the firmware decodes bin i and sleeps
      wait_sleeping;
      repeat (SLEEP_SETTLE_CYCLES) @(posedge clk);       // sleep request propagated, core clock gate closed
      @(negedge osc); clk_run = 0;
      t_act_sum = t_act_sum + ($time - t_act0); if ($time - t_act0 > t_act_max) t_act_max = $time - t_act0;
    end
    t_end = t_start + `N_BINS * `BIN_NS;
    if ($time < t_end) #(t_end - $time);
    rt_marker = ~rt_marker;
    #1;
    win_cyc = gls_cyc - cyc0;
    $display("RT: bins=%0d clk_cycles_in_window=%0d awake_cycles_in_window=%0d active_ns_mean=%0d active_ns_max=%0d overruns=%0d window_ns=%0d",
             `N_BINS, win_cyc, awake_cyc - awake0, t_act_sum / `N_BINS, t_act_max, overruns, t_end - t_start);
    // after the window: wake for the halt (gpio_done must be up: all bins done)
    @(negedge osc); clk_run = 1;
    repeat (4) @(posedge clk);
    if (gpio_done !== 1'b1) $display("WARNING: gpio_done not set after the last bin");
    pulse_wake;
    begin : wait_halt
      for (k = 0; k < `TIMEOUT_CYCLES; k = k + 1) begin
        @(posedge clk);
        if (halted === 1'b1) disable wait_halt;
      end
    end
    if (halted !== 1'b1) begin $display("FAIL: timeout waiting for halt (tohost=%0h)", tohost); $fatal(1); end
    if (tohost == 32'd1 && sram_clk_en === 1'b0 && overruns == 0) begin
      $display("PASS: tohost=%0d (all %0d bins match the reference) sram_clk_en=%0d", tohost, `N_BINS, sram_clk_en);
      $finish;
    end else begin
      $display("FAIL: halted=%b tohost=%h sram_clk_en=%b sleeping=%b overruns=%0d", halted, tohost, sram_clk_en, sleeping, overruns);
      $fatal(1);
    end
  end
endmodule
