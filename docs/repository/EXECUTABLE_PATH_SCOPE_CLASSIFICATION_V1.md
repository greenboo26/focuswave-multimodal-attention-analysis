# Executable path scope classification V1

The clean-clone scan found 97 absolute-path text hits outside `scripts/archive_历史版本/`. Each hit is classified in the CSV as `LEGACY_PROVENANCE_ONLY`: the script is not a current or future canonical entrypoint in `docs/repository/CANONICAL_ENTRYPOINTS_V1.md` or the final analysis surface. Archive-tagged historical producers are therefore not cutover path blockers.

Scoped result: `CURRENT_EXECUTABLE` hits = 0; `LEGACY_PROVENANCE_ONLY` hits = 97; files requiring path normalization in this pass = 0. The current/future surface uses external NIR/RGB producers plus parameterized central contracts/entrypoints; no current canonical local script with an unconfigurable absolute path was found.

This classification does not claim the legacy scripts are portable. It records their exclusion from the Stage 1 blocker under the approved scope and does not authorize bulk legacy normalization.
