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
- external NIR refs: NVIDIA `01af297676399dcf316c1eca8201b4d3aa892023`, AMD `e519373f48c5665226d23334969d419181ccfdda`; read-only comparison found 6,018 common paths, 5,982 identical blobs, 36 differing blobs.

This snapshot is an audit record only. It contains no raw, participant-level or row-level data.
