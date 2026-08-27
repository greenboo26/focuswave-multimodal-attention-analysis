# Validation Threshold Justification

Status: **PASS — thresholds frozen before held-out scoring**

Machine values: `configs/mmwave_reanalysis_v2/benchmark_decision_v1.json`

These are research-validation gates, not a claim of medical-device compliance. No public standard located in Phase 2A supplies one universal numeric acceptance rule for contactless mmWave HR/BR. ISO 80601-2-61:2026 covers pulse-oximeter safety/performance and pulse-rate scope, but its public page does not provide a radar-specific numeric gate. FDA-cleared device summaries and peer radar studies are therefore contextual anchors; the final values are explicitly project-stage decisions.

## Three-layer evidence

| Endpoint | Standard / industry reference | Peer radar reference | Frozen project gate and reason |
|---|---|---|---|
| HR rate | FDA K243687 reports pulse-rate accuracy of ±3 bpm for a cleared video vital-sign device. A clinical wired/wireless comparison predeclared HR LoA within ±5 bpm as acceptable. | A radar systematic review found substantial heterogeneity; 48% of HR studies were within 5% maximum error and 87% within 10%. A dynamic mmWave study reported HR 90th-percentile error below 6 bpm. | Coverage ≥80%; MAE ≤5 bpm; median AE ≤3; RMSE ≤8; |bias| ≤2; LoA inside ±10; Pearson/Spearman ≥0.85; P90 AE ≤10. This is looser than the ±3 bpm cleared-device anchor but requires multiple agreement measures and broad coverage, so a good high-quality subset cannot hide failures. |
| BR rate | FDA K243687 reports ±2 breaths/min; FDA K243765 reports adult impedance RR accuracy ±2 breaths/min. | Dynamic mmWave work reported RR P90 <0.5 rpm in its setting; a radar sleep validation reported 84% coverage and MAE 0.18 rpm, illustrating achievable controlled performance rather than a universal requirement. | Coverage ≥80%; MAE ≤2 rpm; median AE ≤1.5; RMSE ≤3; |bias| ≤1; LoA inside ±5; Pearson/Spearman ≥0.80; P90 AE ≤5. The MAE gate follows the industry anchor; wider LoA acknowledges window-level radar variability while still bounding tails. |
| Beat / IBI | There is no mmWave-specific public standard. Beat timing must first be traceable to QC-passed ECG. | A published noncontact beat study reported IBI bias about −3 ms and LoA roughly −73 to 67 ms; wearable PPG validation can achieve IBI RMS around 23 ms and LoA around ±45 ms, showing that sub-100-ms agreement is meaningful. | Future gate only: coverage ≥80%; precision/recall/F1 ≥0.90; timing and IBI MAE ≤50 ms; |IBI bias| ≤10 ms; LoA inside ±100 ms. The band is deliberately wider than the cited strong results but still requires one-to-one beat fidelity. Passing it does not authorize HRV in V2. |
| Harmonic locks | No relevant regulatory threshold was found. | Radar literature and the project failure audit show that frequency error can be structured rather than random; respiratory harmonics can enter the cardiac band. | 2× HR ≤1%, 0.5× HR ≤1%, and respiratory-harmonic lock ≤2% where valid RSP exists. These are project risk controls: a method with low MAE but recurrent catastrophic locks is not acceptable. Missing RSP means not assessable. |

## Why thresholds are not fitted to historical project scores

Historical AgeBalanced values, quality-stratum values and the known C1/ECG calibration scores were not used to place the acceptance boundary. They remain evidence to reproduce later, not inputs to the gate. The chosen values were frozen from: (1) external device-performance anchors, (2) reported radar/wearable agreement ranges, and (3) the research consequence of a false physiological label. The multi-metric rule also prevents setting a single MAE boundary immediately above an old result.

Coverage uses all reference-valid attempted windows as denominator. Low/rejected radar windows reduce coverage even when no estimate is emitted. Participant coverage must also be at least 80% of the held-out participants (64 of 80 for AgeBalanced). Correlation never substitutes for agreement, and Bland–Altman never substitutes for coverage.

## Sources

- ISO 80601-2-61:2026 scope: https://www.iso.org/standard/84595.html
- FDA K243687: https://www.accessdata.fda.gov/cdrh_docs/pdf24/K243687.pdf
- FDA K243765: https://www.accessdata.fda.gov/cdrh_docs/pdf24/K243765.pdf
- Radar HR/RR systematic review, DOI 10.3390/s24031003: https://pubmed.ncbi.nlm.nih.gov/38339721/
- Dynamic mmWave benchmark: https://arxiv.org/abs/2304.11057
- Radar respiratory-rate validation: https://pubmed.ncbi.nlm.nih.gov/38875674/
- Noncontact IBI study: https://pubmed.ncbi.nlm.nih.gov/36191355/
- Wearable HR/IBI validation: https://pubmed.ncbi.nlm.nih.gov/39529038/
- Clinical wired/wireless agreement study: https://pubmed.ncbi.nlm.nih.gov/36322987/
