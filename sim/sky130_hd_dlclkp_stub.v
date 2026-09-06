// Behavioural stub of sky130_fd_sc_hd__dlclkp_* for RTL simulation only.
`timescale 1ns/1ps
module sky130_fd_sc_hd__dlclkp_1 (GCLK, GATE, CLK);
  output GCLK; input GATE; input CLK; reg en_lat;
  always @(*) if (!CLK) en_lat = GATE;
  assign GCLK = CLK & en_lat;
endmodule
module sky130_fd_sc_hd__dlclkp_2 (GCLK, GATE, CLK);
  output GCLK; input GATE; input CLK; reg en_lat;
  always @(*) if (!CLK) en_lat = GATE;
  assign GCLK = CLK & en_lat;
endmodule
module sky130_fd_sc_hd__dlclkp_4 (GCLK, GATE, CLK);
  output GCLK; input GATE; input CLK; reg en_lat;
  always @(*) if (!CLK) en_lat = GATE;
  assign GCLK = CLK & en_lat;
endmodule
