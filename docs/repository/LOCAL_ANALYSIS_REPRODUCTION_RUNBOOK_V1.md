# Local analysis reproduction runbook V1

Status: `IMPLEMENTATION_BRANCH / COMPLETED_LOCAL_ANALYSES_ONLY`

This runbook standardizes analyses that were already executed on the primary FocusWave workstation. It does **not** authorize new exploratory science and it does not require the colleague/AMD workstation to run questionnaire, behavior or mmWave now.

## 1. Scope

Canonicalized in this pass:

- Beijing behavior/context baseline V2;
- Beijing longitudinal behavior and pre-Probe behavior comparison;
- Q1 questionnaire criterion-validity analysis;
- mmWave C1 alignment robustness audit;
- mmWave M1/Q0 LOSO supporting audit;
- mmWave C2B V2 canonical reconstruction/increment analysis;
- mmWave C2C within-subject resting normalization;
- the already-existing Beijing sensor-increment integration analysis.

NIR/RGB producer engineering remains in the external `kyandi233-dev/Attention-Analysis` repository and is not the primary execution target of this runbook.

## 2. Machine-local paths

Copy the Git-safe template to the already-ignored local file:

```powershell
Copy-Item configs\canonical\paths.local.example.json configs\paths.local.json
```

Edit only `configs/paths.local.json`:

```json
{
  "paths": {
    "raw_data_root": "<this machine's formal raw-data root>",
    "derived_root": "<this machine's derived-data root>",
    "legacy_output_root": "<this machine's retained legacy output root>"
  },
  "analysis_output_overrides": {}
}
```

Do not commit this file. No producer should need a workstation-specific `D:`/`J:` path after launch through the canonical runner.

## 3. Inspect the frozen analysis surface

```powershell
python scripts\canonical\run_local_analysis.py --list
```

The machine-independent scientific registry is:

```text
configs/canonical/local_analysis_registry_v1.json
```

It records the accepted producer, immutable archive provenance and already-frozen scientific settings. Changing windows, labels, folds, seeds, model families or QC rules is outside this reproduction task.

## 4. Preflight before any execution

Example:

```powershell
python scripts\canonical\run_local_analysis.py behavior_baseline_v2 `
  --paths configs\paths.local.json `
  --dry-run
```

A dry-run checks the producer and all registered input paths and prints the resolved output directory. A missing required input is a hard failure; the launcher does not silently substitute another cohort or data root.

## 5. Overwrite policy

The launcher refuses a non-empty output directory by default. On the primary workstation, where accepted historical outputs already exist, do **not** casually use `--force`. Prefer a separate reproduction output using `analysis_output_overrides`, for example:

```json
{
  "analysis_output_overrides": {
    "behavior_baseline_v2": "<derived-root>/reproduction_checks/behavior_baseline_v2"
  }
}
```

`--force` is reserved for a deliberate, reviewed replacement and is never implied by a rerun request.

`behavior_preprobe_v1` is a follow-up producer that historically writes into the longitudinal behavior package. Its existing-output relationship is therefore explicit and should be reviewed before `--force` is used.

## 6. Recommended execution order for a clean machine

The order below follows actual upstream dependencies; it is not a new scientific sequence.

```text
behavior_baseline_v2                     independent from the C2 longitudinal package
behavior_longitudinal_v1                 -> behavior_preprobe_v1
questionnaire_q1_v1                      uses pre-existing questionnaire audit + bridge
mmwave_m1_v1                              supporting raw-mmWave/Q0 audit
mmwave_c2b_v2                             uses frozen C2a + M1 extractor/inputs
mmwave_c2c_v1                             uses C2B canonical feature matrices
mmwave_c1_alignment_v1                    uses already-produced C1c/C1d beat assets only
beijing_sensor_increment_v1              uses already-produced behavior/NIR/mmWave/crosswalk derived tables
```

Examples:

```powershell
python scripts\canonical\run_local_analysis.py behavior_longitudinal_v1 --paths configs\paths.local.json
python scripts\canonical\run_local_analysis.py questionnaire_q1_v1 --paths configs\paths.local.json
python scripts\canonical\run_local_analysis.py mmwave_m1_v1 --paths configs\paths.local.json
python scripts\canonical\run_local_analysis.py mmwave_c2b_v2 --paths configs\paths.local.json
python scripts\canonical\run_local_analysis.py mmwave_c2c_v1 --paths configs\paths.local.json
```

## 7. Provenance written after a successful run

Each canonical launch writes `canonical_run_manifest.json` into that local output package. It records at least:

- analysis ID;
- frozen producer path and producer SHA-256;
- immutable source archive ref;
- current central Git commit when available;
- local path-config SHA-256;
- input file hashes for registered file inputs;
- Python/platform information;
- versions of NumPy, pandas, SciPy, scikit-learn, statsmodels, Matplotlib, vmdpy and bioread when installed;
- completion timestamp.

Absolute local paths remain local. The manifest is evidence for reproducibility; row-level/participant-level products remain excluded from Git unless separately approved.

## 8. Environment lock policy

The repository does not currently contain a trustworthy exact package lock for all historical accepted analyses. Do not manufacture one from guessed versions. The first accepted canonical reproduction on the primary workstation must be checked against the existing accepted aggregate results; its recorded package versions then become the evidence for freezing an environment lock.

Until that check passes, environment status is `CAPTURE_PENDING_ACCEPTED_REPRODUCTION`, not `FULLY_LOCKED`.

## 9. Result-equivalence acceptance

A canonical producer is not considered fully migrated merely because it runs. For each analysis, compare the rerun's Git-safe aggregate tables/report quantities against the already accepted result package from the corresponding archive/canonical result. Acceptance requires:

1. identical cohort/session/participant/probe counts where the result is deterministic;
2. identical frozen windows, labels, folds/groups and model family;
3. deterministic outputs equal where exact equality is expected;
4. floating-point/statistical quantities within a predeclared numerical tolerance only where exact bit identity is not guaranteed;
5. no new exclusions, fallback cohort, post-outcome tuning or silent missing-input substitution;
6. a complete `canonical_run_manifest.json`.

The equivalence check is the next gate before these entrypoints are promoted from `RESTORED_CANONICALIZATION_CANDIDATE` to `CANONICAL_EXECUTABLE`.

## 10. Current boundary

This work packages already-completed local science. It does not alter the existing conclusions: mmWave beat-to-beat HRV is not reopened; C2B/C2C remain the previously adjudicated validation/increment boundary; questionnaire and behavior retain their prior interpretation limits; NIR/RGB formal producer status is unchanged.
