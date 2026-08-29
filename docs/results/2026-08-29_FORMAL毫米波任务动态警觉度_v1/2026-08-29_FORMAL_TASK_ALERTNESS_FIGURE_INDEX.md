# C1 Formal mmWave Task-Dynamics / Alertness Figure Index

Date: 2026-08-29  
Status: **PARTIAL — report-ready aggregation; quality-stratified HR/BR inferential sensitivity remains missing**  
Scope: existing formal mmWave results only; no model refitting, p-value recalculation, classifier retraining, or HR/BR changes.

## Cohort and labeling contract

- `participant N = unresolved`: the source reports anonymous collection batches/session units; it does not establish confirmed independent participant identity.
- Main task-dynamics cohort: session/batch N = 70; window N = 2,237.
- Main alertness event cohort: session/batch N = 70; probe event N = 1,400; paired HR event N = 1,056.
- `MAIN` denotes the existing primary LMM result. `SENSITIVITY` denotes existing GEE, no-harmonic-correction, or fixed-bin results. A sensitivity result is never promoted to primary.
- Values shown in figures and provenance are copied from existing CSV/Markdown fields. Missing CI, p, FDR, or effect fields are not filled in.

## Figure inventory

| Figure | Status | Content | Existing source / annotation boundary |
|---|---|---|---|
| C1 Figure 1A | READY | HR task progression/task dynamics forest | `J_Data_TASK_DYNAMICS_LMM.csv` + `J_Data_TASK_DYNAMICS_GEE.csv`; 2,237 windows / 70 sessions; main and GEE sensitivity shown separately. |
| C1 Figure 1B | READY | BR task progression/task dynamics forest | Same model tables; BR is a secondary exploratory metric and is not presented as confirmed physiology. |
| C1 Figure 2 | READY | Probe pre/post descriptive change by alertness score | `J_Data_ALERTNESS_EVENT_descriptives.csv`; effect = existing descriptive `delta_mean`; CI/p/FDR are **not available** and remain missing. |
| C1 Figure 3 | READY | HR event pre/post effect | Existing LMM primary, GEE sensitivity, no-harmonic-correction sensitivity, and fixed-heart-bin sensitivity. Fixed-bin q = .011 is labeled sensitivity only. |
| C1 Figure 4 | READY | Alertness score distribution + HR alertness terms | Existing event descriptives and LMM/GEE terms; score 1 has only 15 events, retained as a sparse descriptive category. |
| C1 Figure 5 | PARTIAL / COVERAGE-ONLY | HR/BR quality-gated sensitivity status | Existing Issue #15 coverage counts: HR 42/70, BR 50/70 (window+probe), BR 64/70 (probe). No quality-stratified effect estimate/CI/p/FDR exists in source; these fields are marked missing. |

## Missing register

- HR-qualified sensitivity model: **missing**. Existing material provides 42/70 sessions meeting ≥80% paired HR coverage, but no corresponding quality-stratified model coefficient, CI, p, or FDR q.
- BR-qualified sensitivity model: **missing**. Existing material provides 50/70 sessions meeting window+probe ≥80% and 64/70 meeting probe ≥80%, but no corresponding quality-stratified model coefficient, CI, p, or FDR q.
- Probe descriptive CI: **missing**. The source provides pre mean, post mean, delta mean, delta SD, and delta SE; no inferential CI was added.
- Participant-level identity N: **unresolved**. Figures use the source's session/anonymous-batch unit and do not relabel it as confirmed participant N.

## Figure-input QC

- Inferential rows used for Figures 1, 3, and 4 have complete source fields for estimate, 95% CI, p, and FDR q; missing fields in Figures 2 and 5 are intentional source limitations and are labeled in the figures/provenance.
- Figure 2 descriptive inputs have pre mean, post mean, delta mean, event N, session N, and paired-event N; no CI was inferred from delta SD/SE.
- Alertness event counts are unbalanced and copied as 15, 181, 569, and 635 for scores 1–4; score 1 is explicitly flagged as sparse.
- Raw-window outlier screening, distribution-shape testing, and within-group balance testing were not performed because this C1 package reads existing aggregate/model outputs only; no raw data were used.

## Source provenance

The row-level source map is in [`FIGURE_SOURCE_PROVENANCE.csv`](FIGURE_SOURCE_PROVENANCE.csv). The source artifacts were read from `D:\Project\厚粲杯\08_算法`; the original files were not modified.

## Verification boundary

- The 0.08 m/bin audit is treated as **UNAFFECTED** per task instruction; no correction or re-analysis was performed here.
- No p value, FDR q, CI, effect estimate, denominator, HR, or BR value was recomputed.
- Figure labels use `b` for the existing model coefficient and state units; descriptive delta values are labeled as descriptive changes, not model effects.

## Files

- [`C1_Figure01_TaskDynamics_HR_v1.png`](report_ready_mmwave_figures/C1_Figure01_TaskDynamics_HR_v1.png)
- [`C1_Figure01_TaskDynamics_BR_v1.png`](report_ready_mmwave_figures/C1_Figure01_TaskDynamics_BR_v1.png)
- [`C1_Figure02_ProbePrePost_Descriptive_v1.png`](report_ready_mmwave_figures/C1_Figure02_ProbePrePost_Descriptive_v1.png)
- [`C1_Figure03_HRPrePost_EventModel_v1.png`](report_ready_mmwave_figures/C1_Figure03_HRPrePost_EventModel_v1.png)
- [`C1_Figure04_Alertness_DistributionAndHR_v1.png`](report_ready_mmwave_figures/C1_Figure04_Alertness_DistributionAndHR_v1.png)
- [`C1_Figure05_HRBR_QualityGatedSensitivity_Status_v1.png`](report_ready_mmwave_figures/C1_Figure05_HRBR_QualityGatedSensitivity_Status_v1.png)
- [`FIGURE_SOURCE_PROVENANCE.csv`](FIGURE_SOURCE_PROVENANCE.csv)
