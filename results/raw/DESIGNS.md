# Core variants (sky130 TT 1.8 V 25 °C, per-pin OpenSTA power, 20 ns clock)

| design | SRAM macro, sequential (v1) | SRAM sequential, gated membrane groups | std-cell register file (flip-flops), parallel | std-cell latch memory, parallel | latch memory, pipelined W2 read | hardwired weights, parallel | hardwired, 16-bit state, no dense logic | hardwired 16-bit, gated datapath | hardwired 12-bit, gated datapath | hardwired 12-bit, gated, weights pruned to 25 % | hardwired, 16-bit, H=32 | hardwired, 16-bit, H=16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| area, cells + macro (mm²) | 0.684 | 0.72 | 3.23 | 2.17 | 2.29 | 0.441 | 0.327 | 0.307 | 0.282 | 0.219 | 0.152 | 0.0831 |
| std-cell area (mm²) | 0.157 | 0.193 | 3.23 | 2.17 | 2.29 | 0.441 | 0.327 | 0.307 | 0.282 | 0.219 | 0.152 | 0.0831 |
| std cells | 30,251 | 32,883 | 511,493 | 372,115 | 385,176 | 88,404 | 64,126 | 59,547 | 53,951 | 41,491 | 29,762 | 15,835 |
| setup slack @20 ns (ns) | 1.5 | 1.7 | -2.6 | -4 | 0 | 1.3 | 0.05 | 2.4 | 0.59 | 3.1 | 4.2 | 7.4 |
| timing met at all corners | yes | yes | no | no | no | yes | yes | yes | yes | yes | yes | yes |
| test R² (mean of 3 sessions) | 0.583 | 0.583 | 0.583 | 0.583 | 0.583 | 0.583 | 0.583 | 0.583 | 0.582 | 0.574 | 0.572 | 0.555 |
| cycles / bin, event | 185 | 185 | 22.6 | 22.6 | 23.8 | 21 | 21 | 21 | 21 | 20.8 | 20.8 | 20.5 |
| power while decoding, event (µW) | 10,846 | 9,493 | 25,393 | 25,176 | 25,110 | 23,327 | 19,404 | 12,927 | 12,426 | 7,040 | 8,782 | 4,550 |
| energy / bin, event (nJ) | 40.1 | 35.1 | 11.5 | 11.4 | 12 | 9.81 | 8.16 | 5.44 | 5.22 | 2.93 | 3.66 | 1.86 |
| energy / bin, event, SDF (nJ) | 47.3 | 44.5 | -- | -- | -- | 12.1 | 10.3 | 7.12 | 6.79 | 3.44 | 4.43 | 2.24 |
| energy / bin, dense (nJ) | 361 | 353 | 52.6 | 51.8 | 52.8 | 52.7 | -- | -- | -- | -- | -- | -- |
| latency after tick (µs) | 1.66 | 1.66 | 0.14 | 0.14 | 0.16 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 | 0.1 |
| leakage (µW) | 2.54 | 2.52 | 5.68 | 3.4 | 3.4 | 0.674 | 0.495 | 0.461 | 0.436 | 0.346 | 0.167 | 0.0945 |
| idle power, 50 MHz clock running (µW) | 36.4 | 37.2 | 43.8 | 47.1 | 46.8 | 35 | 34.5 | 35.4 | 35.4 | 35.6 | 35 | 35 |
| avg power @250 bins/s, 50 MHz clock (µW) | 46.4 | 45.9 | 46.7 | 49.9 | 49.8 | 37.4 | 36.5 | 36.7 | 36.7 | 36.3 | 35.9 | 35.5 |
| avg power @250 bins/s, 1 MHz clock (µW) | 13.2 | 12 | 9.31 | 7.12 | 7.25 | 3.81 | 3.22 | 2.52 | 2.44 | 1.78 | 1.78 | 1.26 |
| avg power @250 bins/s, clock stopped (µW) | 12.6 | 11.3 | 8.55 | 6.25 | 6.39 | 3.13 | 2.54 | 1.82 | 1.74 | 1.08 | 1.08 | 0.561 |
