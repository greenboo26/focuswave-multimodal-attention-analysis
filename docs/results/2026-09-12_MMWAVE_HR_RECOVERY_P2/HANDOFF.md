# mmWave HR recovery P2 cloud handoff

STATUS: PASS / FAILURE_ATTRIBUTION_COMPLETE

Canonical repository: `greenboo26/focuswave-multimodal-attention-analysis@main`
Canonical commit: `be8c9f0f82b4a99bc6bb438ee0c3267b5310cde1`

Frozen scope: sessions `9779/97793/97794/97795/97796`; 100 probes; DLL host receive/enqueue timestamp; `[probe_end - 30 s, probe_end)`; current per-probe dynamic target; frozen ECG reference.

Control fused/time/spectral HR MAE: `10.4601/8.9695/15.1134 bpm`.

Primary attribution: correct/near-correct 37; selected-target wrong peak 28; harmonic/half-double 18; target/bin/channel miss 17; weak/motion/coverage/ambiguous 0. Fusion versus time improve/worsen/tie=`31/47/22`; versus spectral=`72/19/9`.

Decision: `MAIN_FAILURE_MECHANISM=SELECTED_TARGET_ESTIMATOR_PEAK_AND_FUSION_PATH`; `ROOT_CAUSE_CONFIDENCE=MODERATE`; `P3_EVIDENCE_STATUS=NOT_PRIMARY_BOTTLENECK / NOT_AUTHORIZED_BY_P2`; `NEXT_ROUTE=ESTIMATOR_PATH_NEXT` in a separate controlled task.

Boundaries: ECG was retrospective oracle only after mmWave candidate generation. Formal producer was not modified; no model was trained. HR/BR remains `HOLD / SUPPORTING_ONLY`; HRV remains `BLOCKED`.

Cloud bundle contains only Git-safe report, manifest and aggregate tables. The complete 100-probe attribution table remains local-only at `D:\Project\厚粲杯\11_数据\derived\mmwave_hr_recovery_p2_failure_attribution_20260912_r1\MMWAVE_HR_RECOVERY_P2_ATTRIBUTION_100_PROBES.csv`; SHA-256=`163AEF42BDB30AA4B16A1F89DE22FCCD86799FF1A25B9381734D9D5A3FC3A825`.
