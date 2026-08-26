# Branch retirement matrix V1

The CSV is the authoritative row-level inventory of all 32 fetched `origin/*` branches on 2026-08-26, including actual head SHA and author date. It deliberately records plans only; no remote branch was deleted.

Classification summary: `KEEP_LONG_LIVED` 1; `ACTIVE_TASK_DO_NOT_TOUCH` 3; `MIGRATE_THEN_DELETE` 9; `ARCHIVE_REFERENCE_THEN_DELETE` 18; `HOLD_UNRESOLVED` 1; `SUPERSEDED_SAFE_TO_DELETE_AFTER_AUDIT` 0. Planned delete candidates are therefore 27, all conditional on migration/archive verification and explicit approval. The 3 protected active refs are the candidate, canonicalization and Sol review branches. PR #2 is held unresolved.

The retained result branches were audited as refs, not guessed from chat: report cohort, repeat-session, Q1, final C+B baseline, C1 repair, C2B, C2C, M1 and D1 are mapped to canonical/supporting successors. Their legacy producers remain unmoved because import/path dependencies were not proven safe for physical relocation.
