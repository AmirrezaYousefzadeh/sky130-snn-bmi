// Round 6 (E6): the minimal digital front end and the pruned decoder core as one system, for gate-level co-simulation and
// per-pin power on the routed netlists of both blocks (bmi_fe.nl.v + bmi_snn_sp.nl.v). Structural only: the event handshake, the
// tick and the gated 5 MHz clock connect the two blocks; the weight-write port of the core is tied off (hardwired weights).
module bmi_sys (
  input  wire        clk32k,          // always-on 32.768 kHz clock
  input  wire        clk5,            // 5 MHz oscillator output (running while osc_en)
  input  wire        reset,
  input  wire [95:0] spike_pulse,
  output wire        osc_en,
  output wire        awake,
  output wire        bin_done,
  output wire        out_valid,
  output wire [23:0] y0,
  output wire [23:0] y1,
  output wire        core_clk,        // gated clk5 (observability)
  output wire        ev_valid,
  output wire [6:0]  ev_ch,
  output wire        ev_ready,
  output wire        tick
);
  wire tick_ready, busy, core_clk_en, wr_ready;
  bmi_fe u_fe (.clk32k(clk32k), .clk5(clk5), .reset(reset), .spike_pulse(spike_pulse), .osc_en(osc_en), .core_clk(core_clk),
               .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready), .tick(tick), .tick_ready(tick_ready),
               .out_valid(out_valid), .bin_done(bin_done), .awake(awake));
  bmi_snn_sp u_core (.clk(core_clk), .reset(reset), .mode_dense(1'b0), .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready),
                     .tick(tick), .tick_ready(tick_ready), .out_valid(out_valid), .y0(y0), .y1(y1), .busy(busy), .core_clk_en(core_clk_en),
                     .wr_en(1'b0), .wr_addr(11'd0), .wr_data(32'd0), .wr_ready(wr_ready));
endmodule
