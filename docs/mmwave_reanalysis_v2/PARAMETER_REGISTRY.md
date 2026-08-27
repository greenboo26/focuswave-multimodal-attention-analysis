# Parameter registry

Only parameters actually found in source are listed as frozen historical values. Blank fields are gaps, not defaults.

| ID | Stage | Historical parameter | Source | Data scope | V2 treatment |
|---|---|---|---|---|---|
| P-001 | acquisition/frame | ~100 Hz; 256 range FFT; 8 channels; 3.75 cm/bin | delivery `数据格式说明.md` | early RS6240 | verify per formal manifest |
| P-002 | BR band | 0.1–0.5 Hz in vital scripts; gold RSP QA 0.1–0.7 Hz | v2/v3/v5/v9; `金标准清洗标准.md` | radar vs RSP respectively | preserve as modality-specific candidates; freeze after benchmark |
| P-003 | HR band | 0.8–2.5 Hz | v2/v3/v5/v9 | RS6240 development | benchmark baseline only |
| P-004 | range/bin | power threshold 1% max; SNR-selected channel/bin; v9 phase variance 0.1–50 | v2/v9 | early and pre-experiment | audit target-lock compatibility; do not equate strongest bin with human target |
| P-005 | VMD | alpha=1000, tau=0, K=4, DC=false, init=1, tol=1e-6 | v2/v3/v5 | early development | historical candidate; v3.1.1 uses K=3 in the current source |
| P-006 | notch | Q=30; third harmonic Q=40; fR, 2fR, 3fR | v9 | pre-experiment | ablation candidate; no unverified improvement claim |
| P-007 | peak/IBI | `ecg_reference_v1`: 0.5–40 Hz; robust normalize; both polarities; min distance 0.3 s; prominence 0.25; IBI 300–2000 ms; >=80% valid | `BENCHMARK_DECISION_V1.md` | Movesense/Mindray/BIOPAC raw ECG | FROZEN; >20% adjacent change is a flag, not automatic deletion |
| P-008 | RSP QA | `rsp_reference_v1`: 0.1–0.7 Hz; robust normalize; peak min distance 0.5 s; prominence 0.2; 6–42 RPM; >=80% valid | same | raw Mindray/BIOPAC RSP only | FROZEN; no automatic 17% cycle-jump rejection |
| P-009 | C1b match | one-to-one greedy; ±75 ms primary; ±50/100/150 sensitivity | C1b manifest/report | VS_DATASET | reuse benchmark contract |
| P-010 | windows | primary 30 s / 5 s; HR-only sensitivity 10 s / 5 s; 60 s / 5 s full sensitivity; historical 25 s / 5 s equivalence only | `benchmark_decision_v1.json` | all Phase 2B algorithms | FROZEN |
| P-011 | split | seed 20260827; SHA-256 subject rank; 30 development / 80 held-out | `agebalanced_split_v1.json` | AgeBalanced | FROZEN before scoring |
| P-012 | sync | source-window rate alignment; beat ±75 ms primary and ±50/100/150 sensitivity; no per-window search | `benchmark_decision_v1.json` | beat-capable ECG datasets | FROZEN |
| P-013 | quality | high: timestamp .99, finite .999, gap .2 s, SNR 10 dB, coherence .8; medium: .95/.995/.5 s/3 dB/.5 | same | common radar QC | FROZEN; reference-blind |
| P-014 | HR gate | coverage .80; MAE 5; median AE 3; RMSE 8; correlations .85; bias 2; LoA ±10; P90 10 | `VALIDATION_THRESHOLD_JUSTIFICATION.md` | held-out HR | FROZEN |
| P-015 | BR gate | coverage .80; MAE 2; median AE 1.5; RMSE 3; correlations .80; bias 1; LoA ±5; P90 5 | same | RSP-backed held-out BR | FROZEN |
