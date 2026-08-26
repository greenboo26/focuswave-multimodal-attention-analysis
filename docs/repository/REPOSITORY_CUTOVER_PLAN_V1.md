# Repository cutover plan V1

This document is a future plan, not authorization to cut over now.

1. Freeze task branches and complete GPT/Sol repository final review.
2. Optionally create a recoverable legacy tag after the matrix and migration manifest are approved.
3. Update the candidate entry structure and display documentation; verify all refs and worktrees.
4. Only after explicit approval consider repository display/slug change, then a separately reviewed `master -> main` migration.
5. Update remotes, worktrees, cross-repository refs and team instructions.
6. Delete only branches whose matrix prerequisite is met; never delete an open-PR dependency or active task branch.
7. Run clean-clone, path, contract, staged-content and remote-ref verification.

Rollback conditions: any missing canonical producer, unresolved identity collision, broken import path, failed parity gate, raw/row-level staged asset, default-branch ambiguity, or Sol/GPT review rejection. Rollback means stop the cutover and preserve the candidate/legacy refs; it does not mean deleting data or resetting user work.
