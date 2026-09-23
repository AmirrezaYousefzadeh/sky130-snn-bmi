// Minimal digital front end for the event-driven decoder cores (round 5, E10), version 2: the 5 MHz oscillator is enabled only
// from the bin tick until the core has produced its outputs.
// Always-on domain (clk32k, 32.768 kHz): a 96-bit activity register with set-on-first-event de-duplication, fed by one
// threshold-crossing pulse per channel (one clk32k cycle wide, e.g. the registered comparator output of the analog front end);
// a bin timer of BIN_CYCLES = 131 cycles (3.998 ms). At the bin boundary the activity register is copied to a snapshot
// register and cleared, and the run flag is raised: osc_en enables the 5 MHz oscillator. When the fast domain reports
// completion (done toggle, synchronized), run is cleared; osc_en is held for one more clk32k cycle so that the fast domain
// sees the end of the run before its clock stops.
// Fast domain (clk5, present only while osc_en): a two-flop synchronizer of run, one integrated clock gate for the serializer
// and the decoder core (core_clk). The serializer presents the set bits of the snapshot as AER events, one per cycle, to the
// core's valid/ready handshake, asserts tick for one cycle, waits for out_valid, pulses bin_done for the host, toggles done_tg
// and closes the gate. The affine read-out of the outputs stays in the host, as in the paper.
`timescale 1ns/1ps
module bmi_fe #(
  parameter integer N_CH       = 96,
  parameter integer BIN_CYCLES = 131          // 131 / 32768 Hz = 3.998 ms
)(
  input  wire            clk32k,
  input  wire            clk5,                // 5 MHz oscillator output, running while osc_en (and during reset)
  input  wire            reset,               // synchronous in each domain; hold for >= 2 clk32k cycles with the oscillator running
  input  wire [N_CH-1:0] spike_pulse,         // one pulse per detected spike, synchronous to clk32k
  output wire            osc_en,              // enable of the 5 MHz oscillator
  output wire            core_clk,            // gated clk5 for the decoder core and the serializer
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
  reg            run, hold;
  reg [1:0]      dtg_q;                       // synchronizer of the fast-domain done toggle
  reg            dtg_ack;
  wire           done_tg;
  always @(posedge clk32k) begin
    if (reset) begin cnt <= 8'd0; act <= {N_CH{1'b0}}; snap <= {N_CH{1'b0}}; run <= 1'b0; hold <= 1'b0; dtg_q <= 2'b00; dtg_ack <= 1'b0; end
    else begin
      dtg_q <= {dtg_q[0], done_tg};
      hold <= 1'b0;
      if (cnt == BIN_CYCLES - 1) begin
        cnt <= 8'd0; snap <= act | spike_pulse; act <= {N_CH{1'b0}}; run <= 1'b1;
      end else begin
        cnt <= cnt + 8'd1; act <= act | spike_pulse;
      end
      if (dtg_q[1] != dtg_ack) begin dtg_ack <= dtg_q[1]; run <= 1'b0; hold <= 1'b1; end   // done seen: stop after one more cycle
    end
  end
  assign osc_en = run | hold | reset;
  // ------------------------------------------------------------ fast domain, ungated clk5 (exists only while osc_en)
  reg [1:0] run_q;
  reg       en, done_pending;
  wire      done_pulse;
  always @(posedge clk5) begin
    if (reset) begin run_q <= 2'b00; en <= 1'b0; done_pending <= 1'b0; end
    else begin
      run_q <= {run_q[0], run};
      if (done_pulse) done_pending <= 1'b1; else if (!run_q[1]) done_pending <= 1'b0;
      if (run_q[1] && !done_pending && !done_pulse) en <= 1'b1; else if (done_pulse) en <= 1'b0;
    end
  end
  assign awake = en;
  wire gate_en = en | reset;                   // open during reset so that the gated-domain registers see their reset
  sky130_fd_sc_hd__dlclkp_4 u_icg (.CLK(clk5), .GATE(gate_en), .GCLK(core_clk));
  // ------------------------------------------------------------ event serializer (gated domain)
  localparam [1:0] S_IDLE = 2'd0, S_EVENTS = 2'd1, S_TICK = 2'd2, S_WAIT = 2'd3;
  reg [1:0]      st;
  reg [N_CH-1:0] pending;
  reg            done_q, dtg;
  assign done_pulse = done_q; assign done_tg = dtg;
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
    if (reset) begin st <= S_IDLE; pending <= {N_CH{1'b0}}; ev_valid <= 1'b0; ev_ch <= 7'd0; tick <= 1'b0; bin_done <= 1'b0; done_q <= 1'b0; dtg <= 1'b0; end
    else begin
      done_q <= 1'b0; bin_done <= 1'b0; tick <= 1'b0;
      case (st)
        S_IDLE: if (!done_pending && !done_q) begin pending <= snap; st <= S_EVENTS; end   // the gate delivers one edge after done (done_q still 1, done_pending not yet set): no reload then
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
        S_WAIT: if (out_valid) begin bin_done <= 1'b1; done_q <= 1'b1; dtg <= ~dtg; st <= S_IDLE; end
      endcase
    end
  end
endmodule
