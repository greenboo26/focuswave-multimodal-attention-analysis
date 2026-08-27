# 毫米波任务 2R：AgeBalanced 50 s 外部方法续跑结果

Status: `PARTIAL_DEVELOPMENT_ONLY`

Run date: 2026-08-27

## Scope and execution boundary

Only the frozen AgeBalanced development cohort was used: 30 participants, 60 Lying/Rest and Sitting/Rest sessions, 50 s / 5 s windows, radar 10 Hz, and `ecg_reference_v1`. No held-out participant, formal `J:\Data`, local BIOPAC tuning, BR, HRV, or second external method was used.

The 50 s artifact is `method_native_external_50s`; it is explicitly not a 30 s FocusWave product claim and does not modify `per_window_benchmark_v1`.

## Frozen method implementation

The project route uses historical source lineage `f4a8c74d89ec28e005c537cbd5280a15dcb584e1`, with the same 50 s / 5 s windows and ECG reference as SSA+VMD. A length-preserving phase-difference adapter prepends the first phase sample before differencing; this prevents exact 500-frame recordings from being incorrectly discarded as 499-point signals.

SSA+VMD is a `paper_reimplementation/adapted`, not an official author reproduction. It uses SSA `L=400`, rank `40` from the paper's `0.1L` singular-value rule, VMD `K=5`, `alpha=1000`, `tau=0`, `DC=1`, `init=0`, `tol=1e-6`. The VMD heart mode is selected without ECG by maximal non-DC power in 0.8--2.5 Hz, followed by a periodogram peak in that band. This deterministic mode-selection adapter is explicitly recorded because the paper does not provide author code or a machine-readable mode-index rule for this input.

## Same-condition development comparison

| Metric | Project historical route | SSA+VMD adapted route | External minus project |
|---|---:|---:|---:|
| Attempted windows | 88 | 88 | 0 |
| Scored windows | 81 | 81 | 0 |
| Coverage | 92.05% | 92.05% | 0.00 pp |
| MAE | 29.02 BPM | 28.12 BPM | **-0.90 BPM** |
| Median AE | 15.03 BPM | 15.74 BPM | +0.71 BPM |
| RMSE | 43.10 BPM | 41.72 BPM | -1.38 BPM |
| Pearson r | 0.138 | 0.036 | -0.102 |
| Spearman rho | 0.089 | 0.070 | -0.019 |
| Bland--Altman bias | -25.10 BPM | -19.59 BPM | +5.51 BPM |
| Bland--Altman LoA | [-94.20, 44.00] | [-92.23, 53.05] | not ranked |
| P90 AE | 79.44 BPM | 71.68 BPM | -7.76 BPM |

The external route improves mean absolute error by 0.90 BPM (about 3.1% relative) and RMSE/P90, with no coverage loss. However, median AE is slightly worse, correlations remain near zero, and the error remains far outside the frozen HR gate (MAE 5, median AE 3, RMSE 8 BPM).

## Quality strata and lock audit

| Stratum | Project n / MAE / median AE | SSA+VMD n / MAE / median AE |
|---|---:|---:|
| High | 63 / 29.10 / 13.10 BPM | 63 / 28.43 / 15.74 BPM |
| Medium | 18 / 28.76 / 16.43 BPM | 18 / 27.04 / 14.70 BPM |

The project route had 3 `half_x_hr` classifications and no `two_x_hr`; SSA+VMD had 1 `two_x_hr` and 2 `half_x_hr`. Total obvious 2x/0.5x locks therefore did not decrease. Respiratory-harmonic lock is `NOT_ASSESSABLE` because AgeBalanced has no RSP; it is not zero.

Seven windows failed ECG QC in both routes. The common phase alignment increased the available comparison from the initial 28-window diagnostic to 88 attempted windows; both methods received exactly the same windows and reference QC.

## Decision

Recommendation: `DOWNGRADE_PHYSIOLOGY`.

This is not a claim that SSA+VMD is ineffective. It produced a small, reproducible development improvement without coverage collapse, but not a sufficiently clear or gate-relevant improvement to justify an 80-person run under the competition time budget. The 50 s route also cannot be used as the 30 s product output. Retain mmWave motion/phase/quality features as supporting-signal inputs and prioritize the multimodal AI and psychological-measurement mainline.

The 80-person comparison is not recommended on this evidence. If it is later authorized despite this recommendation, the only admissible configuration is this exact 50 s contract and the two frozen method configs, with no post-result retuning.

## Git-safe provenance

Frozen configuration SHA-256: `29977811e91aea54eb94b69a4ba0587db0a80049cca89aab87df183b1695e57c`.

Local derived outputs are not committed. Their hashes are:

- `method_native_external_50s_project_rows.jsonl`: `25b420aa0c512a9c03da54f51c05cce40776a1a49cf958ce2a9763b19dc09ad3`
- `method_native_external_50s_ssa_vmd_rows.jsonl`: `e11218a4a652cb7b9c18fe1cd5c48a24b8732922dba6e3616d00ceebf374d584`
- `task2r_summary.json`: `c9904dc5f35ef6afe81c4cb65743fdbca9140698093069c19d3ce59945cc7d4e`
- `task2r_config.json`: `4d4694786e952d42f65468da6c063e570796384e1ff5295353679d4e1a24f4ce`

Task 2R is complete. Stop here; do not automatically run 80-person held-out or any later calibration.

## Official AgeBalanced ECG correction

The values in this historical Task 2R report used `ecg_reference_v1` and are retained only as reference-sensitivity diagnostics. The same 50 s radar outputs and routes were rescored with the frozen Official AgeBalanced ECG FFT: project route **9.292 BPM pooled MAE / 7.813 median session-MAE**; SSA+VMD adapted **9.012 / 5.253**; both 88/88 windows and 60/60 sessions. These corrected values supersede 29.02 / 28.12 for AgeBalanced HR performance claims. The small 0.280 BPM pooled difference is not stable across RMSE, extreme errors or lock counts; see `OFFICIAL_REFERENCE_EXISTING_ROUTES_RESULT.md`.
