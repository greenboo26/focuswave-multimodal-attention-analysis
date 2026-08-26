# Local audit snapshot V1

Read-only checks on 2026-08-26 used the actual local roots and Git refs rather than chat paths:

- main repository: `D:\Project\厚粲杯\08_算法`; 261 tracked files, 168 tracked Python files;
- derived root `D:\Project\厚粲杯\11_数据\derived`: present, 174 immediate children;
- `J:\Data`: present, 72 immediate children;
- `I:\预实验`: present, 10 immediate children;
- project management root `D:\Project\厚粲杯\01_管理`: present, 54 immediate children;
- Git worktree listing found the dirty primary checkout plus retained result worktrees and this candidate; no worktree was removed;
- target required directory set: all 31 contract/config/pipeline/result/docs/test paths present;
- remote branch inventory: 32 refs after `fetch origin --prune`; PR #2 head/merge refs were inspected without changing the PR;
- external NIR refs refreshed during this fix: NVIDIA `36a2d596c55b93071a8b5c80459a56c876c06351`, AMD `d8e721079461ef7f71fafcd3edf819858fabbb16`; RGB refs `9b10ca16162ae5f1af5920848e351ec01575bfbc` and `713ef1a780f9a67295c0776c55c20a3d81b4a025`. Historical comparison found 6,018 common paths, 5,982 identical blobs, 36 differing blobs; this remains engineering provenance, not parity proof.

This snapshot is an audit record only. It contains no raw, participant-level or row-level data.
