// Minimal digital front end for the event-driven decoder cores (round 5, E10).
// Always-on domain (clk32k, 32.768 kHz): a 96-bit activity register with set-on-first-event de-duplication, fed by one
// threshold-crossing pulse input per channel (one clk32k cycle wide, e.g. the registered comparator output of the analog
// front end), and a bin timer of BIN_CYCLES = 131 cycles (3.998 ms). At the bin boundary the activity register is copied to
// a snapshot register, cleared, and a wake request is toggled.
// Gated domain (clk5, 5 MHz): a two-flop synchronizer on the free-running clk5 detects the wake request and opens one
// integrated clock gate for the serializer and the decoder core (core_clk). The serializer presents the set bits of the
// snapshot as AER events, one per cycle, to the core's valid/ready handshake, then asserts tick for one cycle, waits for
// out_valid, pulses bin_done for the host, and closes the gate. Between bins only the 32.768 kHz logic and the two
// synchronizer flops are clocked. The affine read-out of the outputs stays in the host, as in the paper.
`timescale 1ns/1ps
module bmi_fe #(
  parameter integer N_CH       = 96,
  parameter integer BIN_CYCLES = 131          // 131 / 32768 Hz = 3.998 ms
)(
  input  wire            clk32k,
  input  wire            clk5,
  input  wire            reset,               // synchronous in each domain; hold for >= 2 clk32k cycles
  input  wire [N_CH-1:0] spike_pulse,         // one pulse per detected spike, synchronous to clk32k
  output wire            core_clk,            // gated clk5 for the decoder core
  output reg             ev_valid,
  output reg  [6:0]      ev_ch,
  input  wire            ev_ready,
  output reg             tick,
  input  wire            tick_ready,
  input  wire            out_valid,
  output reg             bin_done,            // one core_clk cycle: the core outputs of the bin are valid
  output wire            awake                // clock gate open (for the host / debug)
);
  // ------------------------------------------------------------ always-on domain (32.768 kHz)
  reg [7:0]      cnt;
  reg [N_CH-1:0] act, snap;
  reg            wake_tg;
  always @(posedge clk32k) begin
    if (reset) begin cnt <= 8'd0; act <= {N_CH{1'b0}}; snap <= {N_CH{1'b0}}; wake_tg <= 1'b0; end
    else if (cnt == BIN_CYCLES - 1) begin
      cnt <= 8'd0; snap <= act | spike_pulse; act <= {N_CH{1'b0}}; wake_tg <= ~wake_tg;
    end else begin
      cnt <= cnt + 8'd1; act <= act | spike_pulse;
    end
  end
  // ------------------------------------------------------------ wake synchronizer on the free-running clk5
  reg [2:0] tg_q;
  reg       en;
  wire      done;                              // one-cycle pulse from the serializer (gated domain)
  always @(posedge clk5) begin
    if (reset) begin tg_q <= 3'b000; en <= 1'b0; end
    else begin
      tg_q <= {tg_q[1:0], wake_tg};
      if (tg_q[2] ^ tg_q[1]) en <= 1'b1; else if (done) en <= 1'b0;
    end
  end
  assign awake = en;
  wire gate_en = en | reset;                   // the gate is open during reset so that the gated-domain registers see their reset
  sky130_fd_sc_hd__dlclkp_4 u_icg (.CLK(clk5), .GATE(gate_en), .GCLK(core_clk));
  // ------------------------------------------------------------ event serializer (gated domain)
  localparam [1:0] S_IDLE = 2'd0, S_EVENTS = 2'd1, S_TICK = 2'd2, S_WAIT = 2'd3;
  reg [1:0]      st;
  reg [N_CH-1:0] pending;
  reg            done_q;
  reg            tg_seen;                      // last wake request consumed (gated domain); the gate delivers one more edge after
                                               // done, so the load waits for a new request instead of happening in that edge
  assign done = done_q;
  // first set bit: byte-level priority, then bit-level (two shallow stages instead of a 96-deep chain)
  function [6:0] ffs96(input [N_CH-1:0] p);
    integer b, k; reg [11:0] nz; reg [3:0] bsel; reg [7:0] byte_v; reg [2:0] bit_v;
    begin
      for (b = 0; b < 12; b = b + 1) nz[b] = |p[8*b +: 8];
      bsel = 4'd0; for (b = 11; b >= 0; b = b - 1) if (nz[b]) bsel = b[3:0];
      byte_v = p[8*bsel +: 8];
      bit_v = 3'd0; for (k = 7; k >= 0; k = k - 1) if (byte_v[k]) bit_v = k[2:0];
      ffs96 = {bsel, bit_v};
    end
  endfunction
  wire [6:0] first = ffs96(pending);
  always @(posedge core_clk) begin
    if (reset) begin st <= S_IDLE; pending <= {N_CH{1'b0}}; ev_valid <= 1'b0; ev_ch <= 7'd0; tick <= 1'b0; bin_done <= 1'b0; done_q <= 1'b0; tg_seen <= 1'b0; end
    else begin
      done_q <= 1'b0; bin_done <= 1'b0; tick <= 1'b0;
      case (st)
        S_IDLE: if (tg_q[2] != tg_seen) begin tg_seen <= tg_q[2]; pending <= snap; st <= S_EVENTS; end
        S_EVENTS: begin
          if (ev_valid && ev_ready) begin           // event accepted: clear its bit, present the next one (if any)
            pending[ev_ch] <= 1'b0;
            if ((pending & ~({{(N_CH-1){1'b0}}, 1'b1} << ev_ch)) != {N_CH{1'b0}}) begin ev_ch <= ffs96(pending & ~({{(N_CH-1){1'b0}}, 1'b1} << ev_ch)); ev_valid <= 1'b1; end
            else begin ev_valid <= 1'b0; st <= S_TICK; end
          end else if (!ev_valid) begin
            if (pending != {N_CH{1'b0}}) begin ev_ch <= first; ev_valid <= 1'b1; end
            else st <= S_TICK;
          end
        end
        S_TICK: if (tick_ready) begin tick <= 1'b1; st <= S_WAIT; end
        S_WAIT: if (out_valid) begin bin_done <= 1'b1; done_q <= 1'b1; st <= S_IDLE; end
      endcase
    end
  end
endmodule
