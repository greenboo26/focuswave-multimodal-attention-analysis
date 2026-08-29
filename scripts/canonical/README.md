# Canonical local audit entrypoints

本目录只收口事实审计入口，不包含新的科学分析。

- `audit_local_analysis_library.py`：参数化扫描 repo、derived、formal NIR、RGB 和 J 盘根目录，读取轻量 manifest/CSV schema，输出审计 JSON；不复制原始数据、不运行模型、不覆盖结果。
- `../path_registry.py --check`：检查项目登记路径是否存在。

实际科学分析入口必须先在 registry 中登记，并通过存在性、参数化 data/output root、dry-run、manifest、seed/config/code digest 和不覆盖检查后，才可升格为 canonical executable entrypoint。

## 2026-08-29 assimilation boundary

Supporting and validation entrypoints assimilated from the old worktree are
kept in the existing locations:

- `../pipelines/mmwave/`: C2a audit, C1 protocol repair, C1c/C1d pilot
  replay, and C2b task-focus baseline helpers;
- `../scripts/maintenance/`: formal QC, HR course, range-gate, B1/B2,
  readiness, and migration audit helpers;
- `../scripts/build_psychometric_evidence_matrix_v1.py`: corrected
  questionnaire evidence generator;
- `../scripts/legacy/`: 66 historical scripts retained for provenance only.

These additions do not authorize a new full scientific run. Their linked
reports, local output boundaries, conclusions, and decision state are recorded
in `../../docs/canonical/RESULT_INDEX_V1.md` and the assimilation report.
Large outputs remain outside Git and are represented by existing manifests or
small reports.
