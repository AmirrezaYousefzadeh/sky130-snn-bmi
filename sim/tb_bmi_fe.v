// Testbench for the minimal digital front end (bmi_fe): recorded binary channel indicators of N_BINS bins are turned into
// one clk32k-cycle pulses at a random cycle inside each 131-cycle bin; a behavioural decoder core answers the handshake
// (ev_ready with random stalls, out_valid CORE_LAT cycles after tick). Checks that the serialized events of every bin equal
// the recorded set of channels and that exactly one tick is issued per bin. Dumps the front end for power analysis.
`timescale 1ns/1ps
`ifndef N_BINS
  `define N_BINS 500
`endif
`ifndef STREAM_HEX
  `define STREAM_HEX "stream.hex"
`endif
`ifndef MAX_TOKENS
  `define MAX_TOKENS 1400000
`endif
`ifndef CORE_LAT
  `define CORE_LAT 30
`endif
module tb_bmi_fe;
  reg clk32k = 0, osc = 0, reset = 1;
  always #100 osc = ~osc;                       // 5 MHz oscillator; the front end enables it (osc_en) from the tick until the core is done
  always #15258.789 clk32k = ~clk32k;           // 32.768 kHz
  wire osc_en; wire clk5 = osc & osc_en;
  reg  [95:0] spike_pulse = 0;
  wire core_clk, ev_valid, tick, bin_done, awake; wire [6:0] ev_ch;
  reg  ev_ready = 1'b1, tick_ready = 1'b1, out_valid = 1'b0;
  bmi_fe u_fe (.clk32k(clk32k), .clk5(clk5), .reset(reset), .spike_pulse(spike_pulse), .osc_en(osc_en), .core_clk(core_clk),
               .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready), .tick(tick), .tick_ready(tick_ready),
               .out_valid(out_valid), .bin_done(bin_done), .awake(awake));
  // ---- recorded stream: channel tokens terminated by ff per bin
  reg [7:0] stream [0:`MAX_TOKENS-1];
  reg [95:0] rec [0:`N_BINS-1];
  reg [7:0]  pcyc [0:`N_BINS-1][0:95];        // slow cycle of each channel's pulse within its bin
  integer i, b, c, tok, nrec;
  initial begin
    for (i = 0; i < `MAX_TOKENS; i = i + 1) stream[i] = 8'hFE;
    $readmemh(`STREAM_HEX, stream);
    b = 0; i = 0; nrec = 0;
    for (b = 0; b < `N_BINS; b = b + 1) begin rec[b] = 96'd0; for (c = 0; c < 96; c = c + 1) pcyc[b][c] = 0; end
    b = 0;
    while (b < `N_BINS && stream[i] != 8'hFE) begin
      tok = stream[i]; i = i + 1;
      if (tok == 8'hFF) b = b + 1;
      else begin rec[b][tok[6:0]] = 1'b1; pcyc[b][tok[6:0]] = $urandom % 129; nrec = nrec + 1; end   // cycles 0..128 of 131
    end
  end
  // ---- pulse generation, synchronous to clk32k, one bin = 131 slow cycles (aligned with the front end's timer after reset)
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
  // ---- behavioural core: random stalls on ev_ready, out_valid CORE_LAT cycles after tick
  integer lat = -1;
  always @(posedge core_clk) begin
    ev_ready <= ($urandom % 4) != 0;
    out_valid <= 1'b0;
    if (tick) lat <= `CORE_LAT;
    else if (lat > 0) lat <= lat - 1;
    else if (lat == 0) begin out_valid <= 1'b1; lat <= -1; end
  end
  // ---- checking
  reg [95:0] got = 96'd0; integer gbin = 0, errors = 0, nev = 0, nticks = 0, ncore = 0;
  always @(posedge core_clk) begin
    ncore = ncore + 1;
    if (ev_valid && ev_ready) begin got[ev_ch] = 1'b1; nev = nev + 1; end
    if (tick) nticks = nticks + 1;
    if (bin_done) begin
`ifdef FE_DEBUG
      $display("t=%0t bin_done gbin=%0d got=%h rec=%h snap=%h fe.cnt=%0d tb.scnt=%0d tb.sbin=%0d", $time, gbin, got, rec[gbin], u_fe.snap, u_fe.cnt, scnt, sbin);
`endif
      if (got !== rec[gbin]) begin errors = errors + 1; if (errors <= 5) $display("MISMATCH bin %0d: got %h expected %h", gbin, got, rec[gbin]); end
      got = 96'd0; gbin = gbin + 1;
    end
  end
  integer cyc5 = 0; always @(posedge clk5) cyc5 = cyc5 + 1;
  real osc_on = 0; always @(posedge osc) if (osc_en) osc_on = osc_on + 1;
  initial begin
`ifdef DUMP_PATH
    $dumpfile(`DUMP_PATH); $dumpvars(0, tb_bmi_fe.u_fe);
`endif
    repeat (3) @(posedge clk32k); @(negedge clk32k); reset = 0;
    wait (gbin == `N_BINS);
    repeat (20) @(posedge clk5);
    $display("SUMMARY: bins=%0d events=%0d recorded=%0d ticks=%0d errors=%0d clk5_cycles=%0d core_clk_cycles=%0d slow_cycles=%0d osc_on_cycles=%0.0f",
             gbin, nev, nrec, nticks, errors, cyc5, ncore, scnt + 131 * sbin, osc_on);
    if (errors == 0 && nev == nrec && nticks == `N_BINS) $display("PASS: %0d bins, front end serialized every recorded channel exactly once", gbin);
    else $display("FAIL: errors=%0d events=%0d recorded=%0d ticks=%0d", errors, nev, nrec, nticks);
    $finish;
  end
  initial begin #(4.2e6 * (`N_BINS + 3)); $display("FAIL: timeout (bins done %0d)", gbin); $finish; end
endmodule
