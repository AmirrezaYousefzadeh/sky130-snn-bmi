// Round 6 (E6): co-simulation of the front end and the pruned core (rtl/bmi_sys.v on the routed netlists). Same stimulus as
// tb_bmi_fe.v: the recorded channel indicators of N_BINS bins become one-cycle pulses at a random slow cycle inside each 131-cycle
// bin, in real time at 250 bins/s; the 5 MHz oscillator toggles only while the front end enables it. Checks: every recorded
// channel serialized exactly once per bin (front end), one tick per bin, and the core outputs of every bin equal the integer
// reference (EXPECT_HEX, two 32-bit words per bin). Dumps the whole system (DUMP_PATH) for the toggle-based power analysis.
`timescale 1ns/1ps
`ifndef N_BINS
  `define N_BINS 500
`endif
`ifndef STREAM_HEX
  `define STREAM_HEX "stream.hex"
`endif
`ifndef EXPECT_HEX
  `define EXPECT_HEX "expect.hex"
`endif
`ifndef MAX_TOKENS
  `define MAX_TOKENS 1400000
`endif
module tb_bmi_sys;
  reg clk32k = 0, osc = 0, reset = 1;
  always #100 osc = ~osc;                       // 5 MHz oscillator
  always #15258.789 clk32k = ~clk32k;           // 32.768 kHz
  wire osc_en; wire clk5 = osc & osc_en;
  reg  [95:0] spike_pulse = 0;
  wire awake, bin_done, out_valid, core_clk, ev_valid, ev_ready, tick; wire [6:0] ev_ch; wire [23:0] y0, y1;
`ifdef SYS_CORE_LOAD
  // round 7 (fix 7): programmable core (bmi_snn_lmin2 through rtl/bmi_sys_lmin2.v): weights loaded through the write port while the
  // front end is held in reset (its clock gate is open during reset), the dump starts after the load
  reg core_reset = 1, wr_en = 0; reg [10:0] wr_addr = 0; reg [31:0] wr_data = 0; wire wr_ready;
  reg [31:0] weights [0:2047];
  bmi_sys_lmin2 u_sys (.clk32k(clk32k), .clk5(clk5), .reset(reset), .core_reset(core_reset), .spike_pulse(spike_pulse), .wr_en(wr_en), .wr_addr(wr_addr),
                       .wr_data(wr_data), .wr_ready(wr_ready), .osc_en(osc_en), .awake(awake), .bin_done(bin_done), .out_valid(out_valid), .y0(y0), .y1(y1),
                       .core_clk(core_clk), .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready), .tick(tick));
`else
  bmi_sys u_sys (.clk32k(clk32k), .clk5(clk5), .reset(reset), .spike_pulse(spike_pulse), .osc_en(osc_en), .awake(awake), .bin_done(bin_done),
                 .out_valid(out_valid), .y0(y0), .y1(y1), .core_clk(core_clk), .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready), .tick(tick));
`endif
  // ---- recorded stream: channel tokens terminated by ff per bin; expected outputs
  reg [7:0] stream [0:`MAX_TOKENS-1];
  reg [31:0] expect_y [0:2*`N_BINS-1];
  reg [95:0] rec [0:`N_BINS-1];
  reg [7:0]  pcyc [0:`N_BINS-1][0:95];
  integer i, b, c, tok, nrec;
  initial begin
    for (i = 0; i < `MAX_TOKENS; i = i + 1) stream[i] = 8'hFE;
    $readmemh(`STREAM_HEX, stream); $readmemh(`EXPECT_HEX, expect_y);
    b = 0; i = 0; nrec = 0;
    for (b = 0; b < `N_BINS; b = b + 1) begin rec[b] = 96'd0; for (c = 0; c < 96; c = c + 1) pcyc[b][c] = 0; end
    b = 0;
    while (b < `N_BINS && stream[i] != 8'hFE) begin
      tok = stream[i]; i = i + 1;
      if (tok == 8'hFF) b = b + 1;
      else begin rec[b][tok[6:0]] = 1'b1; pcyc[b][tok[6:0]] = $urandom % 129; nrec = nrec + 1; end
    end
  end
  // ---- pulse generation, synchronous to clk32k, one bin = 131 slow cycles
  integer scnt = 0, sbin = 0, k;
  reg [95:0] nxt;
  always @(posedge clk32k) begin
    if (reset) begin scnt <= 0; sbin <= 0; spike_pulse <= 96'd0; end
    else begin
      nxt = 96'd0;
      if (sbin < `N_BINS) for (k = 0; k < 96; k = k + 1) if (rec[sbin][k] && pcyc[sbin][k] == scnt) nxt[k] = 1'b1;
      spike_pulse <= nxt;
      if (scnt == 130) begin scnt <= 0; sbin <= sbin + 1; end else scnt <= scnt + 1;
    end
  end
  // ---- checking: front-end serialization per bin, ticks, and the core outputs against the integer reference
  reg [95:0] got = 96'd0; integer gbin = 0, errors = 0, nev = 0, nticks = 0, ncore = 0, obin = 0, oerrors = 0; reg tick_q = 1'b0;
  always @(posedge core_clk) begin
    ncore = ncore + 1;
    tick_q <= tick;
`ifdef SYS_DEBUG
    if (tick || out_valid || bin_done || (ev_valid && ev_ready)) $display("t=%0t core_clk#%0d tick=%b ev=%b/%0d ready=%b out_valid=%b y0=%h bin_done=%b awake=%b osc_en=%b", $time, ncore, tick, ev_valid, ev_ch, ev_ready, out_valid, y0, bin_done, awake, osc_en);
`endif
    if (ev_valid && ev_ready) begin got[ev_ch] = 1'b1; nev = nev + 1; end
    if (tick && !tick_q) nticks = nticks + 1;     // v3 front end holds tick until the core takes it: count rising edges
    if (out_valid === 1'b1) begin
      if (y0 !== expect_y[2*obin][23:0] || y1 !== expect_y[2*obin+1][23:0]) begin
        oerrors = oerrors + 1; if (oerrors <= 5) $display("OUTPUT MISMATCH bin %0d: got %h %h expected %h %h", obin, y0, y1, expect_y[2*obin][23:0], expect_y[2*obin+1][23:0]);
      end
      obin = obin + 1;
    end
    if (bin_done) begin
      if (got !== rec[gbin]) begin errors = errors + 1; if (errors <= 5) $display("MISMATCH bin %0d: got %h expected %h", gbin, got, rec[gbin]); end
      got = 96'd0; gbin = gbin + 1;
    end
  end
  integer cyc5 = 0; always @(posedge clk5) cyc5 = cyc5 + 1;
  real osc_on = 0; always @(posedge osc) if (osc_en) osc_on = osc_on + 1;
  initial begin
`ifdef SYS_CORE_LOAD
    $readmemh(`WEIGHTS_HEX, weights);
    repeat (3) @(posedge clk32k); @(negedge clk32k); core_reset = 0;          // core out of reset, front end still in reset: core clock runs
    repeat (4) @(posedge core_clk);
    for (i = 0; i < 1664; i = i + 1) begin                                     // W1 rows 0..96 (words 0..1551) and W2 (1600..1663), as tb_bmi_snn
      if (i < 1552 || i >= 1600) begin
        @(negedge core_clk); wr_en = 1'b1; wr_addr = i[10:0]; wr_data = weights[i];
        @(posedge core_clk); while (wr_ready !== 1'b1) @(posedge core_clk);
      end
    end
    @(negedge core_clk); wr_en = 1'b0;
    repeat (4) @(posedge core_clk);
    $display("TB: weights loaded through the write port at t=%0t (core clock cycles %0d)", $time, ncore);
    ncore = 0; cyc5 = 0; osc_on = 0;                                          // the power window starts here
`endif
`ifdef DUMP_PATH
    $dumpfile(`DUMP_PATH); $dumpvars(0, tb_bmi_sys.u_sys);
`endif
`ifdef SYS_CORE_LOAD
    @(negedge clk32k); reset = 0;
`else
    repeat (3) @(posedge clk32k); @(negedge clk32k); reset = 0;
`endif
`ifdef SYS_DEBUG
    $display("t=%0t reset released; osc_en=%b awake=%b core_clk=%b", $time, osc_en, awake, core_clk);
`endif
    wait (gbin == `N_BINS);
    repeat (20) @(posedge clk5);
    $display("SUMMARY: bins=%0d events=%0d recorded=%0d ticks=%0d errors=%0d out_bins=%0d out_errors=%0d clk5_cycles=%0d core_clk_cycles=%0d slow_cycles=%0d osc_on_cycles=%0.0f",
             gbin, nev, nrec, nticks, errors, obin, oerrors, cyc5, ncore, scnt + 131 * sbin, osc_on);
    if (errors == 0 && oerrors == 0 && nev == nrec && nticks == `N_BINS && obin == `N_BINS) $display("PASS: %0d bins, every recorded channel serialized once and every core output bit-exact", gbin);
    else $display("FAIL: errors=%0d out_errors=%0d out_bins=%0d events=%0d recorded=%0d ticks=%0d", errors, oerrors, obin, nev, nrec, nticks);
    $finish;
  end
  initial begin #(4.2e6 * (`N_BINS + 6)); $display("FAIL: timeout (bins done %0d)", gbin); $finish; end
endmodule
