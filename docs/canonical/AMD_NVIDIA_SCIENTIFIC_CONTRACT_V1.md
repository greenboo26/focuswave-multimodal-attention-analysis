# Shared AMD/NVIDIA scientific contract v1

当前状态：`CONTRACT_FROZEN_FOR_REVIEW_NOT_EXECUTION`。本文件冻结语义契约，不证明 CUDA 与 DirectML 数值等价，也不建立 AMD 分支。

## Remote implementation inventory

Read-only ref audit of `kyandi233-dev/Attention-Analysis` on 2026-08-26: `nvidia-cuda=01af297676399dcf316c1eca8201b4d3aa892023`, `amd-DirectML=e519373f48c5665226d23334969d419181ccfdda`. The branches contain 6,038 and 6,069 files; 6,018 paths are common, 5,982 have identical blobs and 36 differ. Identical blobs include vendored/runtime files and are not by themselves scientific parity evidence. The 36 differing paths include `runtime/nir-formal`, `configs`, tests and documentation, so backend branch identity cannot be treated as equivalence.

## Shared contract

- schema：`focuswave-derived-v1`；key=`site + session_id + probe_id`；participant identity is centrally reconciled;
- time：Unix milliseconds; windows are half-open `[probe_onset - window_s, probe_onset)`; timestamp gaps are retained as QC, not silently interpolated;
- labels：1 fully task-focused; 2 experiment-related but not sorting-task-focused; 3 task-unrelated thought; 4 mind blank;
- features：units and definitions must be recorded per column; missingness and QC are explicit;
- provenance fields：`runtime_backend`, `producer_commit`, `model_hash`, `config_digest`, `schema_version`, `source_run_id`;
- primary sensor window：30 s; sensitivities only 10/20 s where predeclared; no best-window selection;
- final common cohort comparison: `C+B`, `C+B+NIR`, `C+B+RGB`, `C+B+NIR+RGB`, identical probes/participants/folds;
- global folds and inferential statistics are centrally created after cross-disk identity reconciliation.

## Backend parity gate

The remote `kyandi233-dev/Attention-Analysis` branch refs must be recorded before execution. Required parity evidence: shared-file blob/hash where identical, backend-specific commit, representative dataset/rows, gross face/ROI/count/missingness/timestamp agreement, and predefined tolerances for continuous features. Semantic mismatches are failures even when numeric error is small; small continuous CUDA/DirectML differences may pass only within the declared tolerance.
