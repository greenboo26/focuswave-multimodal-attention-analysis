# Reproducibility audit v1

## Checks performed

- existence and size scan of repository, derived, formal NIR, RGB, `J:\Data`, `I:\预实验` and independent NIR roots;
- Git branch/commit/worktree inspection;
- manifest JSON and CSV header probes;
- Python syntax compilation of the new read-only canonical audit entrypoint;
- absolute-path search across scripts/configs/docs;
- review of `.gitignore`/`.gitattributes` and raw-data boundary.

## Canonical executable entrypoints

1. `scripts/path_registry.py --check` for configured path presence.
2. `scripts/canonical/audit_local_analysis_library.py` for read-only roots, Git and lightweight manifest/schema inventory.
3. Existing available analysis entrypoints retained as referenced in the registry: `build_evaluate_j_mmwave_m1_loso.py`, `run_beijing_sensor_increment_v1.py`, and `audit_crossmodal_time_gate.py`. Missing historical producers are explicitly marked `UNRESOLVED_MISSING_ENTRYPOINT` in the registry.

## Findings

The new canonical audit is parameterized for repo/data/derived/NIR/RGB/J roots, writes one JSON manifest, does not run science, and does not upload data. Many historical scripts remain non-reproducible without adaptation because they hard-code `D:\Project\厚粲杯\08_算法`, `D:\正式实验`, `D:\acq_mmwave_results`, `J:\预实验`, or another historical checkout. Several behavior and C1/C3 runners live only in prior worktrees. Some manifests lack code/config digest or package lock. These are unresolved and block `CANONICAL_FINAL`.

Known historical syntax failure: `scripts/archive_历史版本/01_旧管线版本/process_vital_signs_v2_0.py:388` contains an incomplete expression. It is archived evidence only and is excluded from active-mainline validation; it was not repaired because Sol explicitly limited recovery to producers needed for retained/future modules.

No overwrite safety can be asserted for every legacy script. A future canonical runner must require an explicit output root, refuse existing outputs unless `--force` is declared, write a manifest, and support site/session filters.
