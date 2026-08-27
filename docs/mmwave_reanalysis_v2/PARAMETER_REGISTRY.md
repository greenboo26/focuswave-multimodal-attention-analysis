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
| P-007 | peak/IBI | ECG QA: min distance 0.3 s, prominence 0.25; IBI 300–2000 ms; >20% change rejected; >=80% valid | `docs/金标准清洗标准.md` | ECG reference | freeze only after per-device audit |
| P-008 | RSP QA | 0.1–0.7 Hz, peak min distance 0.5 s, 6–42 RPM, >=80% valid, no 17% jump rule | same | RSP reference | preserve unless documented update passes audit |
| P-009 | C1b match | one-to-one greedy; ±75 ms primary; ±50/100/150 sensitivity | C1b manifest/report | VS_DATASET | reuse benchmark contract |
| P-010 | windows | historical formal and C2B windows 10/30/60 s; development delivery includes 30 s | registry and scripts | different analyses | V2 primary 30 s, 10/60 sensitivity only after pre-registration |
