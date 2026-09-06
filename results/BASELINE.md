# Sequential SRAM core vs conventional references (sky130 TT 1.8 V 25 °C, 50 MHz, per-pin OpenSTA power on functional gate-level activity)

| metric | sequential SRAM core (event) | dense mode (same netlist) | RISC-V SoC (software) |
|---|---|---|---|
| test R² (mean of 3 Indy sessions) | 0.583 |  |  |
| active cycles / bin | 185 | 1636 | 9030 |
| energy / 4 ms bin, functional activity (nJ) | 40.1 | 361 | 2561 |
| decode latency (µs) | 1.66 | 32.4 | 181 |
| idle power, clock running (µW) | 37.0 | 37.0 | 440 |
| leakage (µW) | 2.54 | 2.54 | 4.67 |
| avg power @250 bins/s, clock running (µW) | 47.1 | 127 | 1081 |
| avg power @250 bins/s, clock stopped (µW) | 12.6 | 93 | 645 |
| area (mm², cells + macro) | 0.684 | same netlist | 1.422 (2 macros) |
| clock (MHz) | 50 | 50 | 50 |
