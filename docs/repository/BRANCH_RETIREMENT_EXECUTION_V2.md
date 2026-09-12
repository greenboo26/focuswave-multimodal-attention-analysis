# FocusWave Branch Retirement Execution Ledger V2 (2026-09-13)

## Scope and baseline

- Repository: `greenboo26/focuswave-multimodal-attention-analysis`
- Default branch at execution: `main`
- Baseline `main` SHA at execution start: `7b68efec5dc545ad832571c5be7db3de347c937c`
- Authorized scope: retire only branches whose live remote tip is already an ancestor of `main`, so that no unique commit becomes unreachable.
- Explicitly out of scope: the ten remaining non-`main` branches, all tag creation/movement, any force push, any branch rename, and any scientific analysis, result, producer, contract, or data change.
- All branch decisions below used live remote refs read immediately before the corresponding operation.

## Method

For every non-`main` remote branch the following checks were run against live refs:

1. existence of a common ancestor with `origin/main` (`git merge-base`),
2. ancestor test (`git merge-base --is-ancestor <branch> origin/main`),
3. unique-commit count (`git rev-list --count origin/main..<branch>`),
4. path-level content comparison against `origin/main` by blob identity,
5. immutable-tag coverage (whether any tag reachable commit equals or contains the branch tip).

A branch was authorized for deletion only when check 2 passed and check 3 returned `0`.

## Deleted branches

Each row below was verified as an ancestor of `origin/main` with zero unique commits. Every commit reachable from these branches is therefore also reachable from `main`, which is the recovery path; no archive tag was required.

| branch | exact SHA | ancestor of `main` | unique commits | last commit |
|---|---|---|---|---|
| `codex/mmwave-estimator-improvement-v1-20260912` | `da84260c87ac581d2a806b06878a33472e0160fc` | yes | 0 | 2026-09-12 23:56:50 +0800 |
| `codex/mmwave-pre30s-selector-hr-20260831` | `2f606cb9332c319993264789061731dd67be064b` | yes | 0 | 2026-08-31 00:40:02 +0800 |
| `codex/t0-vmd-fix` | `018d6f79ec410552ee6f59d6f9f5fb6e8151ce42` | yes | 0 | 2026-08-30 23:57:56 +0800 |

The scientific content of all three branches is already present on `main`: the estimator improvement v1 package under `docs/results/2026-09-12_MMWAVE_ESTIMATOR_IMPROVEMENT_V1/`, the pre-30 s selector rerun under the corresponding canonical pre_30s records, and the VMD regression tests at `tests/test_vmd_backend.py`. Retiring the branch labels changes no result and removes no evidence.

Execution status of this ledger: `DELETION_AUTHORIZED_PENDING`.

## Retained branches and reasons

Ten non-`main` branches were deliberately left untouched.

**Held because an open PR or issue depends on them (5):**

- `codex/formal-bb-behavior-v1` — head of open PR #19 (base `main`).
- `codex/formal-bb-probe-window-fix` — head of open PR #22 (base `codex/formal-bb-behavior-v1`).
- `codex/behavior-science-v3-baseline` — base of open PR #23.
- `codex/behavior-formal-v3-rejected-baseline-fix` — head of open PR #23.
- `fix/issue33-probe-contract` — corresponds to open Issue #33; five files including `docs/results/2026-09-11_ISSUE33_PROBE_REPAIR/REPORT.md` exist nowhere on `main`.

**Held because the branch carries the active report deliverable line (1):**

- `codex/q1-questionnaire-criterion-validity-20260826` — has no common ancestor with `main`; its tip `d8a2870766b011da3d62b85d33dd10652d2db4b4` is 28 commits past its own archive tag `archive/20260826/q1-questionnaire-criterion-validity` (`ba7a2c652bea82c3fa58ad5858a7460ed933fb47`). It is the only place in this repository that tracks `docs/交付/0827报告v1_填充版_20260831.docx`, whose git blob is `10d56a656d1f7cec3de65a6f1ae3e6214691a211` (12196761 bytes) and which `main` does not track at all. The tag commit `ba7a2c6` does not contain that path, so the tag is not a recovery path for the report.

**Held because supersession is established but no immutable tag preserves the content yet (3):**

- `codex/mmwave-formal-reanalysis-v2` — PR #20 base; 42 unique commits and 67 files / +48706 lines concentrated in the pre-restructure `docs|configs|scripts/mmwave_reanalysis_v2/` layout, none of which exists on `main`.
- `codex/mmwave-production-contract-hardening` — head of PR #20, which was closed unmerged with `[SUPERSEDED]` in its title; 74 files / +49447 lines against its base.
- `codex/project-state-map-20260829` — its three changed files all exist on `main` with newer and substantially longer content, but the branch has no tag of its own.

The recommended order for these three is: create `archive/20260913/...` tags first, then delete. That step is outside the currently authorized scope.

**Held as the historical base (1):**

- `master` — unchanged at `96525b19422b34291e4d87747fef214d1fec60d7`, still covered by the immutable rollback tag `legacy/mmwave-hrv-master-pre-focuswave-20260826`. The remote symbolic ref `origin/HEAD` also resolves to this SHA.

## Corrections to earlier records

1. `docs/repository/BRANCH_RETIREMENT_MATRIX_V1.csv` records the `codex/q1-questionnaire-criterion-validity-20260826` row with `head_sha = ba7a2c652bea82c3fa58ad5858a7460ed933fb47`. That is the archive tag commit, not the live branch tip. The live tip is `d8a2870766b011da3d62b85d33dd10652d2db4b4`, 28 commits further on. The V1 row is stale.
2. `docs/repository/BRANCH_RETIREMENT_EXECUTION_V1.md` lists `codex/q1-questionnaire-criterion-validity-20260826` under "Producer branches deleted after preservation checks" and states that each listed branch had a live SHA equal to its archive tag. The live branch was not deleted and its tip no longer equals that tag. The statement does not hold for this row as of 2026-09-13.
3. Neither V1 record covers branches created after 2026-08-29. `BRANCH_RETIREMENT_MATRIX_V2.csv` supersedes the matrix for the current branch surface; V1 is retained unmodified as provenance.

## Rollback and verification state

- `master` remains at `96525b19422b34291e4d87747fef214d1fec60d7`.
- `legacy/mmwave-hrv-master-pre-focuswave-20260826` remains an immutable rollback tag to that exact SHA.
- No archive, legacy, or stage tag was created, deleted, or force-moved by this execution.
- Default branch remains `main`.
- No local branch, worktree, or working-copy file was deleted or moved by this execution.

## Open risks carried forward

These are recorded, not resolved, by this ledger.

1. The primary working copy at `D:\Project\厚粲杯\08_算法` has `HEAD` on `codex/q1-questionnaire-criterion-validity-20260826`, not on `main`. The `main` branch is checked out at `D:\Project\厚粲杯\_t0_vmd_worktree` instead.
2. That primary working copy is dirty (roughly 110 modified, 54 deleted, and 40 untracked entries). Its on-disk content matches `main` far more closely than its `HEAD`, which indicates a partially migrated state. Branch switching from it carries a risk of removing paths that `main` does not track, including the 12 MB report `.docx`.
3. Three independent Git repositories are nested as untracked directories inside that working copy: `FocusWave-Formal-Analysis` (remote `kyandi233-dev/FocusWave-Formal-Analysis`), `Attention-Analysis`, and `01_Attention-Analysis_rgb-nvidia`. A recursive `git clean -fdx` would destroy them.
4. The report `.docx` tracked by the `q1` branch is older than the copy carried by the nested `FocusWave-Formal-Analysis` repository (`514de811092cc488dc3f99afaa574eff23c1e76f`, 10960906 bytes, committed there as `4fe6dd4`). Blob `514de811` does not exist in this repository at all. The report mainline therefore lives in the other repository, and this repository's copy should be treated as a mirror rather than as the authority.
