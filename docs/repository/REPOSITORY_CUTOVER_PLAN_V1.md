# Repository cutover plan V1

This is a future plan only. This fix pass does not create `main`, change the default branch, rename the repository, or delete `master`.

1. Obtain explicit GPT/Sol approval for this candidate's final review fixes. The approved exact head of `codex/focuswave-mainline-restructure-v1`, not old `master`, becomes the source of the new `main`.
2. Before cutover, create the immutable legacy tag `legacy/mmwave-hrv-master-pre-focuswave-20260826` at old `master@96525b19422b34291e4d87747fef214d1fec60d7`. A short-lived rollback ref may also be created.
3. Create `main` from the approved candidate exact SHA. Do not reinterpret the old master as the new mainline.
4. Run clean-clone, contract, path and canonical-result-entry smoke checks. Only after all pass may an authorized operator switch GitHub default branch to `main`.
5. Update local remotes/worktrees, external cross-repository refs and team instructions to the new mainline.
6. Keep old `master` and the immutable legacy tag through the rollback window. After dependency review and explicit approval, delete old `master`; the legacy tag preserves its history.
7. Delete other task branches only when the retirement matrix, producer preservation table, open-PR disposition and archive/migration gates all allow it.

Rollback conditions: missing canonical producer, unresolved identity collision, broken import/path, failed parity or clean-clone gate, raw/row-level staged asset, unresolved PR dependency, default-branch ambiguity, or GPT/Sol rejection. Rollback means stop and retain candidate, old master and legacy refs; it never means destructive reset.
