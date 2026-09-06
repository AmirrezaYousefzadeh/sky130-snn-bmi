# Core variants (sky130 TT 1.8 V 25 °C, per-pin OpenSTA power, 20 ns clock)

| design | SRAM macro, sequential (v1) | std-cell register file, parallel | hardwired weights, parallel | hardwired, 16-bit state, no dense logic | hardwired, 16-bit, H=32 (R2 0.572) | hardwired, 16-bit, H=16 (R2 0.555) |
|---|---|---|---|---|---|---|
| area, cells + macro (mm²) | 0.684 | 3.23 | 0.441 | 0.327 | 0.152 | 0.0831 |
| std-cell area (mm²) | 0.157 | 3.23 | 0.441 | 0.327 | 0.152 | 0.0831 |
| std cells | 30251 | 511493 | 88404 | 64126 | 29762 | 15835 |
| setup slack @20 ns (ns) | 1.49 | -2.62 | 1.3 | 0.0502 | 4.23 | 7.39 |
| cycles / bin, event | 185 | 22.6 | 21 | 21 | 20.8 | 20.5 |
| power while decoding, event (µW) | 1.08e+04 | 2.54e+04 | 2.33e+04 | 1.94e+04 | 8.78e+03 | 4.55e+03 |
| energy / bin, event (nJ) | 40.1 | 11.5 | 9.81 | 8.16 | 3.66 | 1.86 |
| energy / bin, event, SDF (nJ) | 47.3 |  | 12.1 | 10.3 | 4.43 | 2.24 |
| energy / bin, dense (nJ) | 361 | 52.6 | 52.7 |  |  |  |
| latency after tick (µs) | 1.66 | 0.14 | 0.1 | 0.1 | 0.1 | 0.1 |
| leakage (µW) | 2.54 | 5.68 | 0.674 | 0.495 | 0.167 | 0.0945 |
| idle power, 50 MHz clock running (µW) | 36.4 | 43.8 | 35 | 34.5 | 35 | 35 |
| avg power @250 bins/s, 50 MHz clock (µW) | 46.4 | 46.7 | 37.4 | 36.5 | 35.9 | 35.5 |
| avg power @250 bins/s, 1 MHz clock (µW) | 13.2 | 9.31 | 3.81 | 3.22 | 1.78 | 1.26 |
| avg power @250 bins/s, clock stopped (µW) | 12.6 | 8.55 | 3.13 | 2.54 | 1.08 | 0.561 |
