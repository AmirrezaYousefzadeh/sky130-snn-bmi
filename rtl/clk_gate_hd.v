// Integrated clock gate (sky130_fd_sc_hd). RTL sim: behavioural stub in sim/sky130_hd_dlclkp_stub.v
`timescale 1ns/1ps
module clk_gate_hd (
  input  wire clk,
  input  wire en,
  output wire gclk
);
  sky130_fd_sc_hd__dlclkp_4 u_icg (.CLK(clk), .GATE(en), .GCLK(gclk));
endmodule
