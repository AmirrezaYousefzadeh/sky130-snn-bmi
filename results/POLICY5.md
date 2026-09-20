# Utilization policy, round 5: every attempt (from logs/policy_round5.log and logs/orfs5_policy.log)

Policy: start at 60 % core utilization (placement density = utilization + 10 %), step down by 10 % until the run is DRC-clean and meets timing at every signoff corner. A watchdog aborts detailed routing that cannot converge (> 20 k violations after 3 iterations, > 3 k after 8, or no completed iteration for 3 h). Reruns with a hold-repair margin carry the suffix `h`; `lv` marks the 1.28 V signoff (E14).

## Accepted utilizations

| kit | design | accepted util % | attempts (util: outcome) | total runtime (h) |
|---|---|---|---|---|
| SkyWater sky130 (OpenLane) | bmi_snn_sp | 40, 40 (1.28 V) | 60: x; 50: x; 40: ok; 40 lv: ok | 10.0 |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 30h, 20 (1.28 V) | 60: x; 50: x; 40: x; 40: x; 30: x; 20: x; 30h: ok; 30 lv: x; 20 lv: x; 20 lv: ok | 24.0 |
| GF180MCU (OpenLane) | bmi_snn_sp | 50 | 60: x; 50: ok | 1.3 |
| SkyWater sky130 (OpenLane) | bmi_snn_min16 | 60 | 60: ok | 0.1 |
| SkyWater sky130 (OpenLane) | bmi_fe | 60 | 60: ok | 0.1 |
| GF180MCU (OpenLane) | bmi_snn_m12 | 30 | 60: x; 50: x; 40: x; 30: ok | 1.0 |
| SkyWater sky130 (OpenLane) | bmi_snn_top | 60 | 60: ok | 1.1 |
| SkyWater sky130 (OpenLane) | bmi_snn_topg | 40 | 60: x; 50: x; 40: ok | 0.6 |
| GF180MCU (OpenLane) | bmi_snn_min32 | 40 | 60: x; 50: x; 40: ok | 0.4 |
| SkyWater sky130 (OpenLane) | bmi_snn_g16p50 | 60 | 60: ok | 2.3 |
| SkyWater sky130 (OpenLane) | bmi_snn_min32 | 50, 30 (1.28 V) | 60: x; 50: ok; 50 lv: x; 40 lv: x; 30 lv: x; 30 lv: ok | 21.2 |
| SkyWater sky130 (OpenLane) | bmi_snn_ming | 30 | 60: x; 40: x; 30: ok | 11.5 |
| SkyWater sky130 (OpenLane) | bmi_snn_lmin2 | none | 60: x; 30: x; 20: x; 20h: x | 26.2 |
| SkyWater sky130 (OpenLane) | bmi_snn_g32p50 | 50 | 60: x; 50: ok | 7.6 |
| SkyWater sky130 (OpenLane) | bmi_snn_sp_s622 | 40 | 60: x; 40: ok | 8.0 |
| GF180MCU (OpenLane) | bmi_snn_min16 | 50 | 60: x; 50: ok | 5.9 |
| GF180MCU (OpenLane) | bmi_snn_lmin2 | 30h | 30: x; 20: x; 30: x; 20: x; 30h: ok | 14.8 |
| SkyWater sky130 (OpenLane) | bmi_snn_sp_s131 | 40 | 40: ok | 0.3 |
| SkyWater sky130 (OpenLane) | bmi_snn_g32p25 | 50 | 50: ok | 0.4 |
| SkyWater sky130 (OpenLane) | bmi_snn_min | 40 | 60: x; 50: x; 40: ok | 10.2 |
| SkyWater sky130 (OpenLane) | bmi_snn_g64p50 | 30 | 50: x; 40: x; 30: ok | 5.9 |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s622 | 20 | 40: x; 30: x; 20: ok; 30h: x; 20h: x | 12.5 |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s131 | 30h | 30h: ok | 1.5 |
| SkyWater sky130 (OpenLane) | bmi_snn_min32_s622 | 50 | 50: ok | 1.6 |
| SkyWater sky130 (OpenLane) | bmi_snn_lmem | none | 30: x; 20: x | 12.7 |
| SkyWater sky130 (OpenLane) | bmi_snn_g64p125 | 50 | 50: ok | 0.4 |
| SkyWater sky130 (OpenLane) | bmi_snn_min32_s131 | 50 | 50: ok | 1.3 |
| SkyWater sky130 (OpenLane) | bmi_snn_g128p125 | 50 | 50: ok | 1.1 |
| SkyWater sky130 (OpenLane) | bmi_snn_hw | 40 | 60: x; 50: x; 40: ok | 9.9 |
| SkyWater sky130 (OpenLane) | bmi_snn_g128p25 | 30 | 50: x; 40: x; 30: ok | 5.8 |
| SkyWater sky130 (OpenLane) | bmi_snn_scmem | 30 | 40: x; 30: ok | 7.8 |
| SkyWater sky130 (OpenLane) | bmi_snn_g128 | none | 50: x | 3.6 |
| SkyWater sky130 (OpenLane) | bmi_snn_lmem2 | none | 30: x; 20: x | 5.2 |
| NanGate45 (ORFS) | bmi_snn_sp | 60 | 60: ok | 0.2 |
| ASAP7 RVT (ORFS) | bmi_snn_sp | 60 | 60: ok | 0.2 |
| NanGate45 (ORFS) | bmi_snn_m12 | 40 | 60: x; 50: x; 40: ok | 0.8 |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_sp | 60 | 60: ok | 0.3 |
| ASAP7 RVT (ORFS) | bmi_snn_m12 | 50 | 60: x; 50: ok | 0.8 |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_m12 | 50 | 60: x; 50: ok | 0.9 |
| NanGate45 (ORFS) | bmi_snn_min32 | 60 | 60: ok | 0.3 |
| NanGate45 (ORFS) | bmi_snn_min16 | 60 | 60: ok | 0.1 |
| NanGate45 (ORFS) | bmi_snn_lmin2 | 30 | 60: x; 50: x; 40: x; 30: x; 20: x; 30: ok | 1.8 |
| ASAP7 RVT (ORFS) | bmi_snn_min32 | 60 | 60: ok | 0.4 |
| ASAP7 RVT (ORFS) | bmi_snn_min16 | 60 | 60: ok | 0.2 |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | none | 60: x; 50: x; 40: x; 30: x; 20: x; 30: x; 20: x | 2.3 |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_min32 | 60 | 60: ok | 0.3 |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_min16 | 60 | 60: ok | 0.2 |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_lmin2 | none | 60: x; 50: x; 40: x; 30: x; 20: x | 0.0 |
| IHP SG13G2 (ORFS) | bmi_snn_sp | none | 60: x; 50: x; 40: x; 30: x | 13.4 |

## Every attempt

| kit | design | util % | outcome | runtime (min) | reason / note | run tag |
|---|---|---|---|---|---|---|
| SkyWater sky130 (OpenLane) | bmi_snn_sp | 60 | REJECTED | 5 | timing/hold failure | `bmi_snn_sp_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_sp | 50 | REJECTED | 500 | killed: detailed routing hopeless: 4,872 violations after 4 iterations, no progress for 8 h | `bmi_snn_sp_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_sp | 40 | ACCEPTED | 25 |  | `bmi_snn_sp_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_sp | 40 | ACCEPTED (1.28 V signoff) | 70 |  | `bmi_snn_sp_5m_lv` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 60 | REJECTED | 9 | timing/hold failure | `bmi_snn_m12_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 50 | REJECTED | 12 | timing/hold failure | `bmi_snn_m12_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 40 | REJECTED | 500 | killed: GRT-0097 no global routing found; run stalled after CTS | `bmi_snn_m12_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 40 | REJECTED | 215 | watchdog: drt no completed iteration for 3 h (at 0) | `bmi_snn_m12_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 30 | REJECTED | 80 | timing/hold failure | `bmi_snn_m12_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 20 | REJECTED | 10 | killed: hold failure at 30 % is not a utilization problem; rerun at 30 % with hold margin 0.8 ns | `bmi_snn_m12_5m_u20` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 30 | ACCEPTED | 105 |  | `bmi_snn_m12_5m_u30h` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 30 | REJECTED (1.28 V signoff) | 300 | killed: detailed routing wrote no iteration in 3.7 h (stalled start); repeated at 20 % | `bmi_snn_m12_5m_lv` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 20 | REJECTED (1.28 V signoff) | 75 |  | `bmi_snn_m12_5m_lv` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12 | 20 | ACCEPTED (1.28 V signoff) | 135 |  | `bmi_snn_m12_5m_lv` |
| GF180MCU (OpenLane) | bmi_snn_sp | 60 | REJECTED | 3 | timing/hold failure | `bmi_snn_sp_5m_u60` |
| GF180MCU (OpenLane) | bmi_snn_sp | 50 | ACCEPTED | 73 |  | `bmi_snn_sp_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_min16 | 60 | ACCEPTED | 9 |  | `bmi_snn_min16_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_fe | 60 | ACCEPTED | 6 |  | `bmi_fe_5m_u60` |
| GF180MCU (OpenLane) | bmi_snn_m12 | 60 | REJECTED | 7 | timing/hold failure | `bmi_snn_m12_5m_u60` |
| GF180MCU (OpenLane) | bmi_snn_m12 | 50 | REJECTED | 15 | timing/hold failure | `bmi_snn_m12_5m_u50` |
| GF180MCU (OpenLane) | bmi_snn_m12 | 40 | REJECTED | 15 | timing/hold failure | `bmi_snn_m12_5m_u40` |
| GF180MCU (OpenLane) | bmi_snn_m12 | 30 | ACCEPTED | 24 |  | `bmi_snn_m12_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_top | 60 | ACCEPTED | 64 |  | `bmi_snn_top_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_topg | 60 | REJECTED | 14 | timing/hold failure | `bmi_snn_topg_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_topg | 50 | REJECTED | 6 | timing/hold failure | `bmi_snn_topg_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_topg | 40 | ACCEPTED | 15 |  | `bmi_snn_topg_5m_u40` |
| GF180MCU (OpenLane) | bmi_snn_min32 | 60 | REJECTED | 6 | timing/hold failure | `bmi_snn_min32_5m_u60` |
| GF180MCU (OpenLane) | bmi_snn_min32 | 50 | REJECTED | 6 | timing/hold failure | `bmi_snn_min32_5m_u50` |
| GF180MCU (OpenLane) | bmi_snn_min32 | 40 | ACCEPTED | 13 |  | `bmi_snn_min32_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_g16p50 | 60 | ACCEPTED | 138 |  | `bmi_snn_g16p50_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32 | 60 | REJECTED | 470 | killed: detailed routing hopeless: 100,462 violations after 3 iterations | `bmi_snn_min32_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32 | 50 | ACCEPTED | 45 |  | `bmi_snn_min32_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32 | 50 | REJECTED (1.28 V signoff) | 330 | killed: detailed routing 58,294 -> 45,169 violations over 4 iterations with the 1.28 V repair; repeated at 40 % | `bmi_snn_min32_5m_lv` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32 | 40 | REJECTED (1.28 V signoff) | 330 | killed: detailed routing stalled at 9,520 violations after 5 iterations (no progress for 2.7 h); repeated at 30 % | `bmi_snn_min32_5m_lv` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32 | 30 | REJECTED (1.28 V signoff) | 36 |  | `bmi_snn_min32_5m_lv` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32 | 30 | ACCEPTED (1.28 V signoff) | 64 |  | `bmi_snn_min32_5m_lv` |
| SkyWater sky130 (OpenLane) | bmi_snn_ming | 60 | REJECTED | 470 | killed: detailed routing hopeless: 286,322 violations after 1 iteration | `bmi_snn_ming_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_ming | 40 | REJECTED | 175 | watchdog: drt 4211 violations after 8 iterations | `bmi_snn_ming_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_ming | 30 | ACCEPTED | 45 |  | `bmi_snn_ming_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmin2 | 60 | REJECTED | 470 | killed: detailed routing: no iteration completed in 3 h (400k instances) | `bmi_snn_lmin2_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmin2 | 30 | REJECTED | 665 | watchdog: drt 145347 violations after 3 iterations | `bmi_snn_lmin2_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmin2 | 20 | REJECTED | 265 | timing/hold failure | `bmi_snn_lmin2_5m_u20` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmin2 | 20 | REJECTED | 175 | watchdog: drt 93343 violations after 4 iterations | `bmi_snn_lmin2_5m_u20h` |
| SkyWater sky130 (OpenLane) | bmi_snn_g32p50 | 60 | REJECTED | 315 | killed: detailed routing hopeless: 58,769 violations after 3 iterations | `bmi_snn_g32p50_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_g32p50 | 50 | ACCEPTED | 140 |  | `bmi_snn_g32p50_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_sp_s622 | 60 | REJECTED | 455 | killed: detailed routing hopeless: 121,897 violations after 4 iterations | `bmi_snn_sp_s622_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_sp_s622 | 40 | ACCEPTED | 25 |  | `bmi_snn_sp_s622_5m_u40` |
| GF180MCU (OpenLane) | bmi_snn_min16 | 60 | REJECTED | 350 | killed: detailed routing hopeless: 40,924 violations after 4 iterations | `bmi_snn_min16_5m_u60` |
| GF180MCU (OpenLane) | bmi_snn_min16 | 50 | ACCEPTED | 5 |  | `bmi_snn_min16_5m_u50` |
| GF180MCU (OpenLane) | bmi_snn_lmin2 | 30 | REJECTED | 5 | timing/hold failure | `bmi_snn_lmin2_5m_u30` |
| GF180MCU (OpenLane) | bmi_snn_lmin2 | 20 | REJECTED | 5 | timing/hold failure | `bmi_snn_lmin2_5m_u20` |
| GF180MCU (OpenLane) | bmi_snn_lmin2 | 30 | REJECTED | 395 | timing/hold failure | `bmi_snn_lmin2_5m_u30` |
| GF180MCU (OpenLane) | bmi_snn_lmin2 | 20 | REJECTED | 5 | killed: hold failure at 30 % (-0.127 ns at max_ff_n40C_5v50) is not a utilization problem; rerun at 30 % with hold margin 0.8 ns | `bmi_snn_lmin2_5m_u20` |
| GF180MCU (OpenLane) | bmi_snn_lmin2 | 30 | ACCEPTED | 480 |  | `bmi_snn_lmin2_5m_u30h` |
| SkyWater sky130 (OpenLane) | bmi_snn_sp_s131 | 40 | ACCEPTED | 20 |  | `bmi_snn_sp_s131_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_g32p25 | 50 | ACCEPTED | 25 |  | `bmi_snn_g32p25_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_min | 60 | REJECTED | 225 | watchdog: drt 290,447 violations after 1 iteration (killed by hand ahead of the watchdog) | `bmi_snn_min_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_min | 50 | REJECTED | 100 | watchdog: drt 77045 violations after 3 iterations | `bmi_snn_min_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_min | 40 | ACCEPTED | 285 |  | `bmi_snn_min_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_g64p50 | 50 | REJECTED | 80 | watchdog: drt 87987 violations after 3 iterations | `bmi_snn_g64p50_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_g64p50 | 40 | REJECTED | 220 | watchdog: drt no completed iteration for 3 h (at 0) | `bmi_snn_g64p50_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_g64p50 | 30 | ACCEPTED | 55 |  | `bmi_snn_g64p50_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s622 | 40 | REJECTED | 215 | watchdog: drt no completed iteration for 3 h (at 0) | `bmi_snn_m12_s622_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s622 | 30 | REJECTED | 240 | watchdog: drt no completed iteration for 3 h (at 0) | `bmi_snn_m12_s622_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s622 | 20 | ACCEPTED | 40 |  | `bmi_snn_m12_s622_5m_u20` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s622 | 30 | REJECTED | 250 | watchdog: drt no completed iteration for 3 h (at 0) | `bmi_snn_m12_s622_5m_u30h` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s622 | 20 | REJECTED | 5 | killed: duplicate of the accepted 20 % run; the 30 % rerun with the 0.8 ns margin stalled like the original | `bmi_snn_m12_s622_5m_u20h` |
| SkyWater sky130 (OpenLane) | bmi_snn_m12_s131 | 30 | ACCEPTED | 90 |  | `bmi_snn_m12_s131_5m_u30h` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32_s622 | 50 | ACCEPTED | 95 |  | `bmi_snn_min32_s622_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmem | 30 | REJECTED | 490 | watchdog: drt 26272 violations after 4 iterations | `bmi_snn_lmem_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmem | 20 | REJECTED | 270 | watchdog: drt 92394 violations after 3 iterations | `bmi_snn_lmem_5m_u20` |
| SkyWater sky130 (OpenLane) | bmi_snn_g64p125 | 50 | ACCEPTED | 25 |  | `bmi_snn_g64p125_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_min32_s131 | 50 | ACCEPTED | 80 |  | `bmi_snn_min32_s131_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_g128p125 | 50 | ACCEPTED | 65 |  | `bmi_snn_g128p125_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_hw | 60 | REJECTED | 165 | watchdog: drt 121933 violations after 3 iterations | `bmi_snn_hw_5m_u60` |
| SkyWater sky130 (OpenLane) | bmi_snn_hw | 50 | REJECTED | 140 | watchdog: drt 23294 violations after 4 iterations | `bmi_snn_hw_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_hw | 40 | ACCEPTED | 290 |  | `bmi_snn_hw_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_g128p25 | 50 | REJECTED | 165 | watchdog: drt 44899 violations after 4 iterations | `bmi_snn_g128p25_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_g128p25 | 40 | REJECTED | 150 | watchdog: drt 20089 violations after 4 iterations | `bmi_snn_g128p25_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_g128p25 | 30 | ACCEPTED | 35 |  | `bmi_snn_g128p25_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_scmem | 40 | REJECTED | 250 | watchdog: drt 93733 violations after 4 iterations | `bmi_snn_scmem_5m_u40` |
| SkyWater sky130 (OpenLane) | bmi_snn_scmem | 30 | ACCEPTED | 215 |  | `bmi_snn_scmem_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_g128 | 50 | REJECTED | 215 | killed: manual: drt 769k violations, no completed iteration for 2 h; relaunched with 30 20 | `bmi_snn_g128_5m_u50` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmem2 | 30 | REJECTED | 310 | watchdog: drt 125966 violations after 3 iterations | `bmi_snn_lmem2_5m_u30` |
| SkyWater sky130 (OpenLane) | bmi_snn_lmem2 | 20 | REJECTED | 1 | killed: aborted at start: the 30 % run was killed by the default watchdog on the same routing shape that converged for lmin2; relaunched at 30 % with hold margin 1.0 ns and relaxed watchdog | `bmi_snn_lmem2_5m_u20` |
| NanGate45 (ORFS) | bmi_snn_sp | 60 | ACCEPTED | 13 |  | `bmi_snn_sp_5m_u60` |
| ASAP7 RVT (ORFS) | bmi_snn_sp | 60 | ACCEPTED | 15 |  | `bmi_snn_sp_5m_u60` |
| NanGate45 (ORFS) | bmi_snn_m12 | 60 | REJECTED | 13 | flow exit / route did not finish | `bmi_snn_m12_5m_u60` |
| NanGate45 (ORFS) | bmi_snn_m12 | 50 | REJECTED | 10 | flow exit / route did not finish | `bmi_snn_m12_5m_u50` |
| NanGate45 (ORFS) | bmi_snn_m12 | 40 | ACCEPTED | 23 |  | `bmi_snn_m12_5m_u40` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_sp | 60 | ACCEPTED | 16 |  | `bmi_snn_sp_5m_sram_u60` |
| ASAP7 RVT (ORFS) | bmi_snn_m12 | 60 | REJECTED | 19 | flow exit / route did not finish | `bmi_snn_m12_5m_u60` |
| ASAP7 RVT (ORFS) | bmi_snn_m12 | 50 | ACCEPTED | 30 |  | `bmi_snn_m12_5m_u50` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_m12 | 60 | REJECTED | 24 | flow exit / route did not finish | `bmi_snn_m12_5m_sram_u60` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_m12 | 50 | ACCEPTED | 31 |  | `bmi_snn_m12_5m_sram_u50` |
| NanGate45 (ORFS) | bmi_snn_min32 | 60 | ACCEPTED | 16 |  | `bmi_snn_min32_5m_u60` |
| NanGate45 (ORFS) | bmi_snn_min16 | 60 | ACCEPTED | 9 |  | `bmi_snn_min16_5m_u60` |
| NanGate45 (ORFS) | bmi_snn_lmin2 | 60 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u60` |
| NanGate45 (ORFS) | bmi_snn_lmin2 | 50 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u50` |
| NanGate45 (ORFS) | bmi_snn_lmin2 | 40 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u40` |
| NanGate45 (ORFS) | bmi_snn_lmin2 | 30 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u30` |
| NanGate45 (ORFS) | bmi_snn_lmin2 | 20 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u20` |
| NanGate45 (ORFS) | bmi_snn_lmin2 | 30 | ACCEPTED | 107 |  | `bmi_snn_lmin2_5m_u30` |
| ASAP7 RVT (ORFS) | bmi_snn_min32 | 60 | ACCEPTED | 23 |  | `bmi_snn_min32_5m_u60` |
| ASAP7 RVT (ORFS) | bmi_snn_min16 | 60 | ACCEPTED | 14 |  | `bmi_snn_min16_5m_u60` |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | 60 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u60` |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | 50 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u50` |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | 40 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u40` |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | 30 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u30` |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | 20 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u20` |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | 30 | REJECTED | 77 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u30` |
| ASAP7 RVT (ORFS) | bmi_snn_lmin2 | 20 | REJECTED | 61 | flow exit / route did not finish | `bmi_snn_lmin2_5m_u20` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_min32 | 60 | ACCEPTED | 19 |  | `bmi_snn_min32_5m_sram_u60` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_min16 | 60 | ACCEPTED | 10 |  | `bmi_snn_min16_5m_sram_u60` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_lmin2 | 60 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_sram_u60` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_lmin2 | 50 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_sram_u50` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_lmin2 | 40 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_sram_u40` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_lmin2 | 30 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_sram_u30` |
| ASAP7 SRAM-Vt (ORFS) | bmi_snn_lmin2 | 20 | REJECTED | 0 | flow exit / route did not finish | `bmi_snn_lmin2_5m_sram_u20` |
| IHP SG13G2 (ORFS) | bmi_snn_sp | 60 | REJECTED | 490 | flow exit / route did not finish | `bmi_snn_sp_5m_u60` |
| IHP SG13G2 (ORFS) | bmi_snn_sp | 50 | REJECTED | 52 | flow exit / route did not finish | `bmi_snn_sp_5m_u50` |
| IHP SG13G2 (ORFS) | bmi_snn_sp | 40 | REJECTED | 46 | flow exit / route did not finish | `bmi_snn_sp_5m_u40` |
| IHP SG13G2 (ORFS) | bmi_snn_sp | 30 | REJECTED | 214 | flow exit / route did not finish | `bmi_snn_sp_5m_u30` |
