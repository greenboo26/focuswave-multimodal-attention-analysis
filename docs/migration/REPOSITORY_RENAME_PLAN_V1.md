# Repository rename plan v1

日期：2026-08-26
状态：`PLANNED_AFTER_SOL_REVIEW`

## Scope

- old display/repository name: `mmwave-hrv-analysis`
- frozen new display name: `FocusWave Multimodal Attention Analysis`
- proposed new slug: `focuswave-multimodal-attention-analysis`
- current local directory: `D:\Project\厚粲杯\08_算法`；本轮不改名，保留所有既有 worktree 引用。

## Migration actions after Sol approval

1. Rename the GitHub repository/slug and update `origin` with `git remote set-url origin ...`.
2. Update README, handoff documents, CI/connector references, and local worktree documentation.
3. Keep historical branch names and old commit paths intact; add a redirect/alias note rather than rewriting history.
4. Do not move raw data, derived outputs, independent NIR checkout, or user configuration.

## Audit findings

The old name occurs in repository metadata, handoff/protocol text, worktree ledger and collaboration references. Scripts primarily use local roots rather than the repository slug. Several historical scripts additionally contain hard-coded roots (`D:\正式实验`, `D:\acq_mmwave_results`, `J:\预实验`, and the old canonical checkout path); these are recorded as unresolved reproducibility findings, not silently rewritten in this review branch.

## Verification

```powershell
git remote -v
git branch -a
git grep -n "mmwave-hrv-analysis"
git diff --check
git clone --no-local <new-url> <clean-dir>
```

The rename remains explicitly gated on Sol review. No remote slug change is made by this task.
