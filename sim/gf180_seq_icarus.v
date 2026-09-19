// Behavioural GF180MCU sequential cells for SDF-annotated gate-level simulation with Icarus (round 5, E5): the vendor timing
// bodies build the flip-flops and clock gates from UDPs with a notifier and stay X under Icarus. Pin names and specify paths
// follow the vendor wrappers (OpenLane SDF: posedge CLK -> Q, CLK -> Q of the clock gate, D/E -> Q of the latch).
`timescale 1ns/1ps
`celldefine
module gf180mcu_fd_sc_mcu7t5v0__dffq_1 (CLK, D, Q);
  input CLK, D; output Q; reg Q;
  always @(posedge CLK) Q <= D;
  specify
    (posedge CLK => (Q : D)) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__icgtp_1 (TE, E, CLK, Q);
  input TE, E, CLK; output Q; reg en_l;
  always @(CLK or E or TE) if (!CLK) en_l = E | TE;
  assign Q = CLK & en_l;
  specify
    (CLK => Q) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__latq_1 (E, D, Q);
  input E, D; output Q; reg Q;
  always @(E or D) if (E) Q = D;
  specify
    (D => Q) = (0, 0);
    (posedge E => (Q : D)) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__dffq_2 (CLK, D, Q);
  input CLK, D; output Q; reg Q;
  always @(posedge CLK) Q <= D;
  specify
    (posedge CLK => (Q : D)) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__icgtp_2 (TE, E, CLK, Q);
  input TE, E, CLK; output Q; reg en_l;
  always @(CLK or E or TE) if (!CLK) en_l = E | TE;
  assign Q = CLK & en_l;
  specify
    (CLK => Q) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__latq_2 (E, D, Q);
  input E, D; output Q; reg Q;
  always @(E or D) if (E) Q = D;
  specify
    (D => Q) = (0, 0);
    (posedge E => (Q : D)) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__dffq_4 (CLK, D, Q);
  input CLK, D; output Q; reg Q;
  always @(posedge CLK) Q <= D;
  specify
    (posedge CLK => (Q : D)) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__icgtp_4 (TE, E, CLK, Q);
  input TE, E, CLK; output Q; reg en_l;
  always @(CLK or E or TE) if (!CLK) en_l = E | TE;
  assign Q = CLK & en_l;
  specify
    (CLK => Q) = (0, 0);
  endspecify
endmodule

module gf180mcu_fd_sc_mcu7t5v0__latq_4 (E, D, Q);
  input E, D; output Q; reg Q;
  always @(E or D) if (E) Q = D;
  specify
    (D => Q) = (0, 0);
    (posedge E => (Q : D)) = (0, 0);
  endspecify
endmodule

`endcelldefine