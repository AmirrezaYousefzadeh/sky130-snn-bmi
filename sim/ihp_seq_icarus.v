// Behavioural IHP SG13G2 sequential cells for SDF-annotated gate-level simulation with Icarus (round 5, E5).
// The vendor models (IHP-Open-PDK sg13g2_stdcell.v) compute their state from the delayed_* nets of $setuphold checks through
// UDP-like helper modules with a notifier; Icarus leaves that state X (see the round-2 note in results/run_log*.md), so the
// functional model set /media/pdk/ihp_sg13g2_models_functional.v was generated for zero-delay runs. For annotated runs these
// modules keep the vendor pin names and IOPATH paths (SDF from OpenSTA write_sdf) and are compiled together with the vendor
// combinational cells (sequential modules stripped: /media/pdk/icarus_sdf_models/sg13g2_stdcell_seqstripped.v).
`timescale 1ns/10ps

module sg13g2_dfrbp_1 (Q, Q_N, CLK, D, RESET_B);
  output Q, Q_N; input CLK, D, RESET_B; reg Q, Q_N;
  always @(posedge CLK or negedge RESET_B) if (!RESET_B) begin Q <= 1'b0; Q_N <= 1'b1; end else begin Q <= D; Q_N <= ~D; end
  specify
    (CLK => Q) = (0, 0); (CLK => Q_N) = (0, 0); (RESET_B => Q) = (0, 0); (RESET_B => Q_N) = (0, 0);
  endspecify
endmodule

module sg13g2_dfrbp_2 (Q, Q_N, CLK, D, RESET_B);
  output Q, Q_N; input CLK, D, RESET_B; reg Q, Q_N;
  always @(posedge CLK or negedge RESET_B) if (!RESET_B) begin Q <= 1'b0; Q_N <= 1'b1; end else begin Q <= D; Q_N <= ~D; end
  specify
    (CLK => Q) = (0, 0); (CLK => Q_N) = (0, 0); (RESET_B => Q) = (0, 0); (RESET_B => Q_N) = (0, 0);
  endspecify
endmodule

module sg13g2_dfrbpq_1 (Q, CLK, D, RESET_B);
  output Q; input CLK, D, RESET_B; reg Q;
  always @(posedge CLK or negedge RESET_B) if (!RESET_B) Q <= 1'b0; else Q <= D;
  specify
    (CLK => Q) = (0, 0); (RESET_B => Q) = (0, 0);
  endspecify
endmodule

module sg13g2_dfrbpq_2 (Q, CLK, D, RESET_B);
  output Q; input CLK, D, RESET_B; reg Q;
  always @(posedge CLK or negedge RESET_B) if (!RESET_B) Q <= 1'b0; else Q <= D;
  specify
    (CLK => Q) = (0, 0); (RESET_B => Q) = (0, 0);
  endspecify
endmodule

// integrated clock gate: GATE captured while CLK is low, GCLK = CLK & captured GATE
module sg13g2_lgcp_1 (GCLK, CLK, GATE);
  output GCLK; input CLK, GATE; reg en_l;
  always @(CLK or GATE) if (!CLK) en_l = GATE;
  assign GCLK = CLK & en_l;
  specify
    (CLK => GCLK) = (0, 0);
  endspecify
endmodule
