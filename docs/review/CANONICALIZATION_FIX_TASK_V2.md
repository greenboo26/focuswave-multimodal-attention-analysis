# CANONICALIZATION FIX TASK V2 — final small fixes

Source review: `docs/review/SOL_REREVIEW_V1.md`  
Reviewed correction commit: `ce4da877743132d6a8b4f21a298c58b1b06f3f5e`  
Verdict: `AMD_HANDOFF_APPROVAL = APPROVED_AFTER_FINAL_SMALL_FIXES`

## Branch and scope

Continue on:

`codex/local-analysis-library-canonicalization-20260826`

Do not modify the Sol review branch. Do not create the AMD execution branch yet.

This is a small closure pass. Do not re-audit the whole local library, do not rebuild all 29 historical cards, and do not start new exploratory sensor analyses.

## Required blocking fixes

### 1. Create the standalone AMD execution surface

Create `docs/canonical/AMD_EXECUTION_RUNBOOK_V1.md` and, where useful, focused executable contracts/cards for the modules that can actually run on the colleague workstation.

At minimum cover:

- local session/data discovery and linkage-evidence export;
- NIR DirectML production + QC;
- RGB Face DirectML production + QC;
- RGB Pose/Motion production + QC if part of the handoff;
- standardized Probe-window export/adapters;
- local output packaging for central merge;
- central-only identity, folds and final inference boundary.

For each executable module record exact:

- repository and approved ref/commit;
- script/entrypoint;
- config path;
- model asset path/hash where applicable;
- required local input fields/root parameters;
- output root parameter;
- output schema and units;
- timestamps/gaps policy;
- QC/pass/fail policy;
- resume/completion/overwrite behavior;
- manifest/provenance fields;
- preflight/dry-run command;
- pass condition and stop condition.

Do not require a colleague to reconstruct an execution rule from a generic method-card paragraph plus another manifest.

Historical/supporting-only method cards may remain concise if they are explicitly marked non-executable/historical and their producer/result provenance is already adequate.

### 2. Fix window definitions by modality

Update `AMD_NVIDIA_SCIENTIFIC_CONTRACT_V1.md`, relevant registry rows and future-main cards so they agree:

- Behavior C+B baseline: primary 30 s; sensitivities 10/20 s.
- NIR increment: primary 30 s; sensitivities 10/60 s.
- Existing mmWave analyses: preserve their executed 10/30/60 definitions; no cosmetic rerun.
- RGB increment: freeze its window definition **before** final prediction modeling. Use a scientifically justified predeclared sensitivity rule and record it; do not choose it after observing AUC.
- Multimodal primary fusion: exact matched common cohort at the predeclared 30 s primary window unless a later Sol-approved written protocol explicitly changes this before results are viewed.

Remove any generic statement that silently forces all sensors to 10/20 s.

### 3. Clarify local/global identity schema

Update `DERIVED_DATA_CONTRACT_V1.md` and the runbook.

Preferred explicit fields/roles:

- stable session key (`site + session_id/single_experiment_id`);
- local linkage evidence / `local_participant_linkage_key` or equivalent when deterministically known on that disk;
- `identity_status`;
- `global_repeat_participant_id` generated only at central reconciliation.

If backward-compatible exports retain a column named `repeat_participant_id`, specify whether it is local/provisional or central-authoritative. The AMD machine must not invent a global participant identifier merely to populate a required field.

### 4. Run vigilance proportional-odds sensitivity

Use the already frozen 1,400-probe / 46-participant Beijing report cohort. Do not change the main predictors.

Create one small parameterized diagnostic runner or extend the existing report runner without changing its original results.

Fit participant-clustered binary logistic GEE models for cumulative thresholds:

- `vigilance >= 2`;
- `vigilance >= 3`;
- `vigilance >= 4`.

Use the same relevant progress/block predictors as the current ordinal analysis. For the probe-state relation, apply equivalent threshold-specific models using the same state and time covariates.

Export Git-safe aggregate coefficients/ORs/95% CIs and a short interpretation stating whether common-odds direction is sufficiently coherent. No alternate threshold search.

### 5. Run Q1 proportional-odds sensitivity

Use the same 67-session canonical questionnaire bridge and same standardized predictors as the existing Q1 OrderedModel.

Because the fourth category is empty, fit the two observed cumulative thresholds:

- `mind_wandering_ordinal >= 2`;
- `mind_wandering_ordinal >= 3`.

Use participant-cluster robust inference. Preserve the existing predictor definitions and multiplicity family; do not search new questionnaire items or models.

Publish a Git-safe aggregate sensitivity table and short interpretation.

### 6. Freeze parity Gate 0

Update `AMD_NVIDIA_SCIENTIFIC_CONTRACT_V1.md` from review-only prose into an executable gate specification and reference it from the AMD runbook.

RGB:
- record the existing AMD real-300 CPU-reference↔DirectML evidence as passed for the AMD Py-Feat 2.1.1 scientific core;
- record that NVIDIA CPU-reference↔CUDA parity remains a separate NVIDIA gate if it has not yet been completed;
- do not compare different subjects across disks as if they were row-wise parity.

NIR:
- define the exact representative sample/reference to be used for AMD Gate 0;
- compare frame/timestamp identity, YOLO detection/ROI coverage, RITnet/fullclass outputs, missingness/QC and key continuous quantities under predefined tolerances;
- record model hashes/config/runtime backend;
- if Gate 0 fails, bulk AMD NIR production does not start.

If a suitable NIR representative reference output already exists locally, use it; otherwise create only the minimal representative parity evidence, not a bulk rerun.

### 7. Finish retained provenance identifiers

For retained/current results, replace shortened producer SHAs such as `ba7a2c6` / `97b236a` with verified full 40-character commit SHAs in `PRODUCER_PROVENANCE_V1.md`, the registry and executable runbook where relevant.

Supporting historical rows that have no required future execution path may remain explicitly unresolved.

## Required before final report, but not AMD-branch blocker after the above passes

### A. Pre-Probe error sensitivity

Add a predefined 10/20/30 s binomial-GEE sensitivity using the available error numerator/denominator (or a canonical trial-level logistic equivalent) with the same label contrast, `probe_progress`, `block_num` and participant clustering. Preserve the current Gaussian-GEE result as a descriptive/continuous-rate analysis if desired; do not tune windows based on the new result.

### B. Corrected canonical Q1 semantic note

Publish a current canonical Q1 result note/table with code 3=`task-unrelated thought`, code 4=`mind blank`. Historical files remain immutable provenance. Verify the code-to-column relationship before carrying numerical effects into the corrected table.

## Validation before returning

Run and report at least:

- registry CSV parse and retained-current full-SHA checks;
- focused compilation/tests for new or modified active scripts;
- ordinal sensitivity output schema parse;
- AMD runbook path/ref/script/config checks against current Git refs;
- no raw/row-level participant data staged;
- no AMD execution branch created;
- clean worktree and pushed remote SHA match.

Return exactly:

`READY_FOR_SOL_FINAL_GATE`

plus branch, commit SHA, and a compact table mapping Fix V2 items 1–7 to evidence paths/results. Also report the headline threshold-specific ordinal sensitivity results and whether NIR/RGB Gate 0 is `PASS`, `READY_TO_RUN`, or `BLOCKED`.
