// bmi_snn_top — event-driven streaming SNN decoder for intracortical BMI (NeuroBench primate reaching).
//
// 96 input channels -> H LIF neurons -> 2 leaky-integrator outputs (finger velocity), integer arithmetic.
// Weights (int8) live in one SRAM22 2048x32 macro:  W1[c][4w+l] @ word c*16+w byte l (c=0..96, row 96 = bias),
//                                                    W2[j][i]    @ word 1600+j byte i.
// Two operating modes on the same netlist:
//   mode_dense=0  event-driven: every accepted input event (channel id) immediately streams the 16 weight
//                 words of its row and accumulates into the H membranes (activity-proportional work).
//   mode_dense=1  dense baseline: events only set bits of an input vector; on tick all 96 rows are visited
//                 (multiply-by-0/1 gating), i.e. what a conventional MAC engine does without zero-skipping.
// tick (end of 4 ms bin): bias row, then a two-stage pipelined leak/threshold/reset scan of the H neurons
// (one per cycle); each hidden spike fetches its W2 word and accumulates the two outputs; out_valid pulses with y0/y1.
//
// Clock gating: an always-on enable register drives an integrated clock gate; everything but that
// register (FSM, neuron state, SRAM) runs on core_clk, which stops whenever the core is idle.
`timescale 1ns/1ps

module bmi_snn_top #(
  parameter integer H     = 64,     // hidden neurons (multiple of 4)
  parameter integer THETA = 256,    // firing threshold (membrane units)
  parameter integer K1    = 4,      // hidden leak: v -= v >>> K1
  parameter integer K2    = 4       // output leak: o -= o >>> K2
)(
  input  wire        clk,
  input  wire        reset,        // synchronous, active high
  input  wire        mode_dense,
  // input events (AER-style handshake)
  input  wire        ev_valid,
  input  wire [6:0]  ev_ch,
  output wire        ev_ready,
  // end-of-bin tick (handshake)
  input  wire        tick,
  output wire        tick_ready,
  // decoded output (two int24 accumulator values)
  output reg         out_valid,
  output wire [23:0] y0,
  output wire [23:0] y1,
  output wire        busy,
  output wire        core_clk_en,
  // weight-memory write port (host load; idle-only)
  input  wire        wr_en,
  input  wire [10:0] wr_addr,
  input  wire [31:0] wr_data
);
  localparam integer NW      = H / 4;          // words per W1 row
  localparam integer W2_BASE = 1600;
  localparam [1:0] S_IDLE = 2'd0, S_ROW = 2'd1, S_NSCAN = 2'd2, S_OUT = 2'd3;

  // ------------------------------------------------------------------ always-on domain
  reg  [1:0]  state;
  reg         rd_pend;
  reg         acc_valid;
  reg         scan_valid;
  reg         en_q;
  wire        en_d = reset | ev_valid | tick | wr_en | (state != S_IDLE) | rd_pend | acc_valid | out_valid | scan_valid;
  always @(posedge clk) en_q <= en_d;
  assign core_clk_en = en_q;

  wire core_clk;
  sky130_fd_sc_hd__dlclkp_4 u_icg (.CLK(clk), .GATE(en_q), .GCLK(core_clk));

  // ------------------------------------------------------------------ gated domain
  reg  [6:0]        row;        // current W1 row (0..96)
  reg  [3:0]        widx;       // word issue counter
  reg               in_tick;
  reg               row_gate;   // accumulate enable for the row being streamed
  reg  [95:0]       x;          // dense-mode input vector
  reg  [6:0]        j;          // neuron scan index
  reg  [3:0]        rd_widx;
  reg               rd_gate;
  reg               rd_is_w2;
  reg  [31:0]       dout_r;        // registered SRAM output (breaks the macro -> adder -> membrane path)
  reg  [3:0]        acc_widx;
  reg               acc_gate, acc_is_w2;
  reg  signed [19:0] v [0:H-1];
  reg  signed [23:0] o0, o1;
  // neuron-scan pipeline (stage A: read membrane; stage B: leak / threshold / reset / W2 fetch)
  reg  signed [19:0] vj_r;
  reg  [6:0]         j_r;
  reg  [1:0]         out_cnt;

  assign y0 = o0;
  assign y1 = o1;
  assign busy = (state != S_IDLE) | rd_pend | acc_valid | scan_valid;
  wire idle_awake = (state == S_IDLE) & en_q & ~wr_en;
  assign ev_ready   = idle_awake;
  assign tick_ready = idle_awake & ~ev_valid;

  // SRAM control (registered-output macro: dout valid the cycle after ce)
  reg          mem_ce, mem_we;
  reg  [10:0]  mem_addr;
  wire [31:0]  mem_dout;
  wire         wmem_ce = mem_ce;
  wire         wmem_we = mem_we;

  // saturating 20-bit add of an int8
  function signed [19:0] sat_add20(input signed [19:0] a, input signed [7:0] w);
    reg signed [20:0] s;
    begin
      s = {a[19], a} + {{13{w[7]}}, w};
      if (s > 21'sd524287)       sat_add20 = 20'sd524287;
      else if (s < -21'sd524288) sat_add20 = -20'sd524288;
      else                       sat_add20 = s[19:0];
    end
  endfunction
  // saturating 24-bit add of an int8
  function signed [23:0] sat_add24(input signed [23:0] a, input signed [7:0] w);
    reg signed [24:0] s;
    begin
      s = {a[23], a} + {{17{w[7]}}, w};
      if (s > 25'sd8388607)       sat_add24 = 24'sd8388607;
      else if (s < -25'sd8388608) sat_add24 = -24'sd8388608;
      else                        sat_add24 = s[23:0];
    end
  endfunction

  // neuron-scan datapath (stage B operates on the registered membrane vj_r)
  wire signed [19:0] vl  = vj_r - (vj_r >>> K1);
  wire               spk = (vl >= THETA);

  // control: which read to issue this cycle
  reg        issue_row;        // issue W1 word (row, widx)
  reg        last_word;
  integer    l, n;

  always @(*) begin
    issue_row = (state == S_ROW);
    last_word = (widx == NW - 1);
    mem_ce   = 1'b0;
    mem_we   = 1'b0;
    mem_addr = 11'd0;
    if (state == S_IDLE && wr_en) begin
      mem_ce = 1'b1; mem_we = 1'b1; mem_addr = wr_addr;
    end else if (issue_row) begin
      mem_ce = 1'b1; mem_addr = {row, 4'd0} + {7'd0, widx};
    end else if (scan_valid && spk) begin
      mem_ce = 1'b1; mem_addr = W2_BASE + {4'd0, j_r};
    end
  end

  always @(posedge core_clk) begin
    if (reset) begin
      state <= S_IDLE; row <= 7'd0; widx <= 4'd0; in_tick <= 1'b0; row_gate <= 1'b0;
      x <= 96'd0; j <= 7'd0; rd_pend <= 1'b0; rd_widx <= 4'd0; rd_gate <= 1'b0; rd_is_w2 <= 1'b0;
      out_valid <= 1'b0; o0 <= 24'sd0; o1 <= 24'sd0;
      vj_r <= 20'sd0; j_r <= 7'd0; scan_valid <= 1'b0; out_cnt <= 2'd0;
      dout_r <= 32'd0; acc_widx <= 4'd0; acc_gate <= 1'b0; acc_is_w2 <= 1'b0; acc_valid <= 1'b0;
      for (n = 0; n < H; n = n + 1) v[n] <= 20'sd0;
    end else begin
      out_valid <= 1'b0;
      // ---------------- read-data pipeline: issue -> (SRAM latency) -> register dout -> accumulate
      rd_pend <= 1'b0;
      acc_valid <= rd_pend;
      if (rd_pend) begin
        dout_r <= mem_dout; acc_widx <= rd_widx; acc_gate <= rd_gate; acc_is_w2 <= rd_is_w2;
      end
      if (acc_valid) begin
        if (!acc_is_w2) begin
          if (acc_gate)
            for (l = 0; l < 4; l = l + 1)
              v[{acc_widx, 2'd0} + l] <= sat_add20(v[{acc_widx, 2'd0} + l], dout_r[8*l +: 8]);
        end else begin
          o0 <= sat_add24(o0, dout_r[7:0]);
          o1 <= sat_add24(o1, dout_r[15:8]);
        end
      end
      // ---------------- neuron-scan stage B (independent of state)
      scan_valid <= 1'b0;
      if (scan_valid) begin
        v[j_r[5:0]] <= spk ? 20'sd0 : vl;
        if (spk) begin rd_pend <= 1'b1; rd_is_w2 <= 1'b1; end
      end
      // ---------------- FSM
      case (state)
        S_IDLE: begin
          if (wr_en) begin
            // memory write handled combinationally
          end else if (ev_valid) begin
            if (mode_dense) begin
              x[ev_ch] <= 1'b1;
            end else begin
              row <= ev_ch; row_gate <= 1'b1; widx <= 4'd0; state <= S_ROW; in_tick <= 1'b0;
            end
          end else if (tick) begin
            in_tick <= 1'b1; widx <= 4'd0; state <= S_ROW;
            if (mode_dense) begin row <= 7'd0;  row_gate <= x[0]; end
            else            begin row <= 7'd96; row_gate <= 1'b1; end
          end
        end
        S_ROW: begin
          rd_pend <= 1'b1; rd_widx <= widx; rd_gate <= row_gate; rd_is_w2 <= 1'b0;
          widx <= widx + 4'd1;
          if (last_word) begin
            widx <= 4'd0;
            if (!in_tick) begin
              state <= S_IDLE;
            end else if (row == 7'd96) begin
              state <= S_NSCAN; j <= 7'd0;
            end else begin
              row <= row + 7'd1;
              row_gate <= (row == 7'd95) ? 1'b1 : x[row + 7'd1];
            end
          end
        end
        S_NSCAN: begin
          // stage A: read one membrane per cycle
          if (j == 7'd0) begin
            o0 <= o0 - (o0 >>> K2);
            o1 <= o1 - (o1 >>> K2);
          end
          vj_r <= v[j[5:0]]; j_r <= j; scan_valid <= 1'b1;
          j <= j + 7'd1;
          if (j == H - 1) begin state <= S_OUT; out_cnt <= 2'd0; end
        end
        S_OUT: begin
          // cycle 1: stage B of the last neuron (may issue its W2 read); cycle 2: register dout; cycle 3: accumulate
          out_cnt <= out_cnt + 2'd1;
          if (out_cnt == 2'd2) begin
            state <= S_IDLE; in_tick <= 1'b0; x <= 96'd0; out_valid <= 1'b1;
          end
        end
      endcase
    end
  end

  sram22_2048x32m8w8 u_wmem (
    .clk   (core_clk),
    .rstb  (~reset),
    .ce    (wmem_ce),
    .we    (wmem_we),
    .wmask (4'hF),
    .addr  (mem_addr),
    .din   (wr_data),
    .dout  (mem_dout)
  );
endmodule
