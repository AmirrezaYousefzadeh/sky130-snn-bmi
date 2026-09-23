// Round 7 (fix 7): the minimal digital front end and the gated 12-bit latch-memory core (bmi_snn_lmin2) as one system, for
// gate-level co-simulation and per-pin power on the routed netlists of both blocks. As rtl/bmi_sys.v, plus: the core's weight-write
// port is exposed (the weights are loaded by the testbench through it before decoding, as a host would), and the core has its own
// reset so that it can be loaded while the front end is still held in reset (the front end opens the core clock gate during reset).
module bmi_sys_lmin2 (
  input  wire        clk32k,          // always-on 32.768 kHz clock
  input  wire        clk5,            // 5 MHz oscillator output (running while osc_en)
  input  wire        reset,           // front-end reset (also opens the core clock gate)
  input  wire        core_reset,
  input  wire [95:0] spike_pulse,
  input  wire        wr_en,
  input  wire [10:0] wr_addr,
  input  wire [31:0] wr_data,
  output wire        wr_ready,
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
  wire tick_ready, busy, core_clk_en;
  bmi_fe u_fe (.clk32k(clk32k), .clk5(clk5), .reset(reset), .spike_pulse(spike_pulse), .osc_en(osc_en), .core_clk(core_clk),
               .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready), .tick(tick), .tick_ready(tick_ready),
               .out_valid(out_valid), .bin_done(bin_done), .awake(awake));
  bmi_snn_lmin2 u_core (.clk(core_clk), .reset(core_reset), .mode_dense(1'b0), .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready),
                        .tick(tick), .tick_ready(tick_ready), .out_valid(out_valid), .y0(y0), .y1(y1), .busy(busy), .core_clk_en(core_clk_en),
                        .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data), .wr_ready(wr_ready));
endmodule
