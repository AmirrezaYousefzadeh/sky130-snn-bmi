// Yosys latch techmap for gf180mcu_fd_sc_mcu7t5v0 (the PDK's OpenLane directory references latch_map.v but does not ship it).
module \$_DLATCH_P_ (input E, input D, output Q);
  gf180mcu_fd_sc_mcu7t5v0__latq_1 _TECHMAP_DLATCH_P (.D(D), .E(E), .Q(Q));
endmodule
module \$_DLATCH_N_ (input E, input D, output Q);
  wire nE; gf180mcu_fd_sc_mcu7t5v0__inv_1 _TECHMAP_DLATCH_N_INV (.I(E), .ZN(nE));
  gf180mcu_fd_sc_mcu7t5v0__latq_1 _TECHMAP_DLATCH_N (.D(D), .E(nE), .Q(Q));
endmodule
