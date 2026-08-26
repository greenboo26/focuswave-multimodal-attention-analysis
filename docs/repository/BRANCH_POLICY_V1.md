# Branch policy V1

The formal repository branch surface is `main` with `master` retained during the rollback window. External producer refs are recorded by exact commit, not mirrored as permanent branches. Task branches are ephemeral and are retired after merge/close and immutable preservation checks. Governance/review branches are retired only after their successor documents are present on `main`.
