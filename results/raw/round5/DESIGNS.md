# Core variants, round 5 (sky130 TT 1.8 V 25 C, 5 MHz, per-pin OpenSTA power)

| core | util % | area mm2 | cells | setup ns | hold ns | cyc/bin | E nJ | E ann. nJ | leak logic uW | leak total uW | P_stop uW | P_32k uW | P_5M uW | E full blocks (A/B/C) nJ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bmi_snn_top | -- | 0.643 | 13,479 | 117 | 0.111 | -- | -- | -- | 2.39 | 2.44 | -- | -- | -- | --/--/-- |
| bmi_snn_topg | -- | 0.69 | 20,914 | 118 | 0.557 | -- | -- | -- | 2.4 | 2.58 | -- | -- | -- | --/--/-- |
| bmi_snn_min16 | 60 | 0.0655 | 9,150 | 117 | 0.114 | 20.5 | 1.69 | 2.06 | 0.03 | 0.0641 | 0.58 | 0.604 | 4.33 | --/--/-- |
| bmi_snn_g16p50 | 60 | 0.0542 | 7,359 | 116 | 0.318 | 20.6 | 0.93 | 1.1 | 0.0254 | 0.0464 | 0.321 | 0.345 | 3.96 | --/--/-- |
