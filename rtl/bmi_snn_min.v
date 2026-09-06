// Energy-minimised top: hardwired weights, parallel datapath, 16-bit membranes and outputs, no dense-mode logic.
`timescale 1ns/1ps
module bmi_snn_min #(parameter integer H = 64, THETA = 256, K1 = 4, K2 = 4)(
  input  wire clk, input wire reset, input wire mode_dense,
  input  wire ev_valid, input wire [6:0] ev_ch, output wire ev_ready,
  input  wire tick, output wire tick_ready,
  output wire out_valid, output wire [23:0] y0, output wire [23:0] y1,
  output wire busy, output wire core_clk_en,
  input  wire wr_en, input wire [10:0] wr_addr, input wire [31:0] wr_data);
  wire [15:0] y0_16, y1_16;
  bmi_snn_par #(.H(H), .THETA(THETA), .K1(K1), .K2(K2), .HARDWIRED(1), .V_BITS(16), .O_BITS(16), .DENSE(0)) u_core (
    .clk(clk), .reset(reset), .mode_dense(1'b0), .ev_valid(ev_valid), .ev_ch(ev_ch), .ev_ready(ev_ready),
    .tick(tick), .tick_ready(tick_ready), .out_valid(out_valid), .y0(y0_16), .y1(y1_16), .busy(busy), .core_clk_en(core_clk_en),
    .wr_en(1'b0), .wr_addr(11'd0), .wr_data(32'd0));
  assign y0 = {{8{y0_16[15]}}, y0_16};
  assign y1 = {{8{y1_16[15]}}, y1_16};
endmodule
