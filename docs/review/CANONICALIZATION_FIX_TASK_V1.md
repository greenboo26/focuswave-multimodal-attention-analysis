# CANONICALIZATION FIX TASK V1

Source review: `docs/review/SOL_SCIENTIFIC_REVIEW_V1.md`  
Review verdict: `AMD_HANDOFF_APPROVAL = APPROVED_AFTER_FIXES`

## Execution branch

Return to and update:

`codex/local-analysis-library-canonicalization-20260826`

Do not modify the Sol review branch. Do not create the AMD execution branch yet.

## Scope

This is a correction/canonicalization pass, not a new exploratory analysis cycle. Use local files and historical Git branches to recover factual producer/provenance details. Run a scientific analysis only when the review explicitly requires a canonical rerun because an existing final result cannot otherwise be verified.

## Required corrections

### A. Rebuild the registry as a real scientific registry

For all 29 analysis IDs:

1. verify the actual producer script from the branch/commit that produced the result;
2. record exact producer branch and commit;
3. distinguish producer script from supporting/upstream scripts;
4. correct cohort/session/probe counts;
5. correct status according to the Sol review matrix;
6. record whether the module is:
   - historical only;
   - final-report supporting;
   - required future main analysis;
   - local derived production for colleague;
   - global-only inference.

Explicit corrections already verified:

- report cohort / four-class / vigilance / Probe-vigilance -> `scripts/run_report_cohort_label_vigilance_v1.py` from commit `67851bff212fc1e73b9611ac5de670581e316cc7`;
- repeat-session -> `scripts/run_report_repeat_session_effects_v1.py` from commit `c2de2af3ba6fd46d351c4da4fcf05e281f982cff`;
- questionnaire Q1 -> `scripts/run_q1_questionnaire_criterion_validity.py` from its actual result branch/commit;
- do not retain `72 sessions/1400 probes` for behavior baseline.

### B. Replace generic method cards

For every retained/required analysis, create a real method card with:

- question;
- exact inputs + required columns;
- exact producer;
- cohort;
- unit;
- labels;
- windows;
- QC;
- formula/model;
- participant dependence;
- CV/preprocessing;
- CI/bootstrap/FDR;
- outputs + schemas;
- aggregate completed result or planned result contract;
- interpretation boundary;
- local/AMD/global execution role.

No card may use only `见 registry` or `见 local manifest` for a field needed to execute or interpret the analysis.

### C. Canonical behavior baseline

Inspect local `final_report_cohort_baseline_v2`.

If it is a real completed run:
- verify exactly 70 sessions / 46 participants / 1400 probes;
- verify model definition unchanged from V1;
- identify actual runner/config/seed;
- upload only Git-safe aggregate report, metrics, calibration summary, and redacted manifest;
- register it as the current Beijing canonical behavior/context baseline.

If it is not a valid completed run, create/recover a parameterized runner and rerun only this predefined analysis on the 70/1400 report cohort.

Do not create global folds yet.

### D. Probe-before behavior validity

Locate the actual final state-contrast analysis that tests Probe state vs preceding error/RT for the predefined windows.

If completed, upload its Git-safe aggregate package and exact producer/provenance.

If no independently reproducible final package exists, run one canonical predefined analysis using the already frozen label semantics and windows. Do not search new windows/models. Record FDR family and participant dependence.

### E. Fix label and status semantics

- canonical mapping everywhere: 3 = task-unrelated thought, 4 = mind blank;
- correct Q1 prose accordingly;
- EARLY_INCREMENT = SUPERSEDED;
- C3A_V1/V2 = SUPERSEDED_INTERMEDIATE;
- NIR_69 split/rename as engineering fullclass completion, not final NIR increment;
- C1 = valid stopped-validation boundary, not simple external-storage blocker;
- D1 = DEFERRED_EXTERNAL_STORAGE_NOT_AVAILABLE.

### F. Local-vs-global identity and folds

Rewrite the derived contract so that the colleague machine exports local identity/linkage evidence and stable session keys, but does not independently freeze global `repeat_participant_id` when cross-disk duplicates are possible.

Central integration must:
1. merge linkage evidence;
2. resolve cross-disk natural-person identity;
3. freeze global `repeat_participant_id`;
4. create global participant-disjoint folds.

### G. Shared AMD/NVIDIA scientific contract

Using `kyandi233-dev/Attention-Analysis`, explicitly inventory the current remote `nvidia-cuda` and `amd-DirectML` implementations.

Do not assume branch equivalence. Freeze and document:
- shared scientific schema/version;
- timestamps and gap semantics;
- feature definitions/units;
- sampling rates;
- QC rules;
- model hashes;
- backend-specific code commits;
- runtime backend field;
- representative parity test dataset/rows;
- parity metrics/tolerances;
- acceptable numeric differences vs unacceptable semantic differences.

Where a shared scientific-layer file is identical across both branches, record its blob/hash as evidence.

### H. Software/provenance

For modules intended for colleague execution, provide a reproducible environment snapshot/lock and manifest requirements: Python, package versions, seed, code commit, config digest, model hash, schema, output root, overwrite/resume policy.

### I. Minimal colleague execution surface

Produce a draft `AMD_EXECUTION_MODULES_V1.md` that includes only what the colleague actually needs to run on her disk.

Do not make her reproduce all 29 historical analyses.

At minimum distinguish:
- local data/session discovery + provenance;
- behavior/Probe derived production if those files exist on her disk;
- questionnaire bridge if questionnaires exist there;
- NIR AMD production/QC;
- RGB AMD production/QC;
- mmWave derived production only if the external disk contains required mmWave and Sol-approved final plan still needs the cross-site ablation;
- global-only analyses that she must not run independently.

## Completion criteria

Return `READY_FOR_SOL_REREVIEW` only when:

- all retained method cards are non-generic;
- producer mappings are verified;
- 70/1400 behavior baseline is reviewable;
- Probe-before behavior validity is reviewable;
- label/status errors are fixed;
- local/global identity boundary is explicit;
- AMD/NVIDIA parity contract is explicit;
- colleague module list is minimal and executable;
- no AMD execution branch has been created;
- all Git-safe result packages required for review are on the canonicalization branch.

Push and report branch + commit SHA + a checklist mapping every Sol critical fix to its resolution.
