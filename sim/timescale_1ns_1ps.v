// Round 5: compiled first so that vendor model files without a `timescale directive (GF180 primitives) do not inherit Icarus's
// default time unit; with the models compiled before the testbench the GF180 clock buffers resolved to X under -gspecify.
`timescale 1ns/1ps
