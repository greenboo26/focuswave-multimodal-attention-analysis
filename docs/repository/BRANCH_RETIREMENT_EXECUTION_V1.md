# FocusWave Stage 2B Branch Retirement Execution Ledger

## Scope and baseline

- Repository: `greenboo26/focuswave-multimodal-attention-analysis`
- Default branch at execution: `main`
- Stage 2B scope: PR #2 base/disposition pre-processing and safe retirement of completed task branches.
- No scientific analysis, pipeline, result, NIR/RGB/mmWave asset, or legacy-path normalization was changed.
- All branch decisions below used live remote refs immediately before the corresponding operation. The candidate row in `BRANCH_RETIREMENT_MATRIX_V1.csv` was not rewritten to self-reference this execution commit.

## PR #2 disposition

PR #2 remains `KEEP_OPEN_AND_UPDATE`: open, not merged, and not closed. Its base was retargeted from `master` to `main` because the available GitHub API supported the operation. The live post-retarget state is:

- head: `chatgpt/multimodal-results-nir-diagnostic-20260826@0e756b275fd9cbbc7d7564531d3200425bf3be23`
- base: `main@526baf389be67848654b381fc9e8b0880b2ed6e3`
- mergeability at final read: `true`
- disposition: deferred for later scientific/repository review; no merge or close was performed.

## Producer branches deleted after preservation checks

Each branch had a live SHA equal to its pre-existing immutable producer archive tag, a supporting/canonical successor on `main`, and no open PR dependency. The nine producer archive tags remain untouched.

| branch | preserved archive tag | exact SHA |
|---|---|---|
| `codex/c1-alignment-protocol-repair-20260826` | `archive/20260826/c1-alignment-protocol-repair` | `73bcca8051847e111f8bb217368f56d7a2b7f42f` |
| `codex/c2b-v2-canonical-20260826` | `archive/20260826/c2b-v2-canonical` | `c889dd0d24daf58bf751d0e01780717c72a81abe` |
| `codex/c2c-within-subject-normalization-20260826` | `archive/20260826/c2c-within-subject-normalization` | `afcbed32c74439995a20354d694677380ab3f5f2` |
| `codex/d1-beijing-zhuhai-canonical-20260826` | `archive/20260826/d1-beijing-zhuhai-canonical` | `bb5535b97b04e315d3cdb748ef1cb8e8778a7939` |
| `codex/final-report-cohort-baseline-v2` | `archive/20260826/final-report-cohort-baseline-v2` | `414a4f46c8d058961a87750345d06a7129afc9f2` |
| `codex/m1-mmwave-person-effect-audit-20260826` | `archive/20260826/m1-mmwave-person-effect-audit` | `70c8ab1bbe02012b01916e4894af2e6d74eedfe0` |
| `codex/q1-questionnaire-criterion-validity-20260826` | `archive/20260826/q1-questionnaire-criterion-validity` | `ba7a2c652bea82c3fa58ad5858a7460ed933fb47` |
| `codex/report-cohort-label-vigilance-20260826` | `archive/20260826/report-cohort-label-vigilance` | `67851bff212fc1e73b9611ac5de670581e316cc7` |
| `codex/report-repeat-session-effects-20260826` | `archive/20260826/report-repeat-session-effects` | `c2de2af3ba6fd46d351c4da4fcf05e281f982cff` |

## Retired branches and immutable retirement tags

The following branches passed live-SHA, immutable-tag, no-open-PR, and archive/successor evidence checks and were deleted. Their tags remain on the remote.

| deleted branch | retirement archive tag | exact SHA |
|---|---|---|
| `codex/audit-j-target-lock-gate` | `archive/20260826/retired/codex-audit-j-target-lock-gate` | `f997d75e2009c56d7ca9b2ebd2169fbe2ed393d8` |
| `codex/c1-alignment-audit-20260826` | `archive/20260826/retired/codex-c1-alignment-audit-20260826` | `ac9b2c3f20bbefa6f4d00ecb145b5983def5d99f` |
| `codex/c1a-preflight-sync` | `archive/20260826/retired/codex-c1a-preflight-sync` | `76573b0cdddd27c414b39ca71e565bf0377a65d6` |
| `codex/c1c-c1d-handoff-20260826` | `archive/20260826/retired/codex-c1c-c1d-handoff-20260826` | `5cd2be69e7764a125242a4e2406e8d9a79d7c0f9` |
| `codex/c2c3-audit-handoff` | `archive/20260826/retired/codex-c2c3-audit-handoff` | `8d33ae11805f12a24d5b9fbbe1792da188833885` |
| `codex/c2c3-handoff` | `archive/20260826/retired/codex-c2c3-handoff` | `e1aa14474c55ee630bb6eaf58fa139f45fe35190` |
| `codex/c3-multimodal-readiness-and-baseline-20260826` | `archive/20260826/retired/codex-c3-multimodal-readiness-and-baseline-20260826` | `455755bf66e37ab17dd9b961e6ff5dd83e7ea16e` |
| `codex/c3a-formal-nir-full-v2-20260826` | `archive/20260826/retired/codex-c3a-formal-nir-full-v2-20260826` | `add2b62d3331ecd35c9a93f0d68804730442c6d4` |
| `codex/common-longitudinal-handoff` | `archive/20260826/retired/codex-common-longitudinal-handoff` | `f4714248c5ac09806555a1ad6a737254297a3b03` |
| `codex/final-behavior-context-baseline-20260826` | `archive/20260826/retired/codex-final-behavior-context-baseline-20260826` | `f7b0542e0b19a74a3f00035c758ae95145f7ef43` |
| `codex/gpt-audit-baseline-nir-v1` | `archive/20260826/retired/codex-gpt-audit-baseline-nir-v1` | `b8c1e62e86142fbd42faad1ec0dd654df02fdee9` |
| `codex/gpt-codex-handoff-20260825` | `archive/20260826/retired/codex-gpt-codex-handoff-20260825` | `4e0f1aaa195f8346df4794da03527f383bf05db0` |
| `codex/protocol-identity-update-20260826` | `archive/20260826/retired/codex-protocol-identity-update-20260826` | `6e2eda0af827c7a6bff8056ec7d1e79bef955336` |
| `codex/rs6240-sol-review-20260825` | `archive/20260826/retired/codex-rs6240-sol-review-20260825` | `49552a96d7e7665cca6f700bbad2a561db7f6d05` |
| `experimental/formal-v311-ab-20260825` | `archive/20260826/retired/experimental-formal-v311-ab-20260825` | `aeb5e39cb0a6529f1bd1d4549826f05d72ad2743` |
| `sample/formal-mmwave-v1` | `archive/20260826/retired/sample-formal-mmwave-v1` | `4af812701d2814b948c8320ab64a5a14bcce76e7` |
| `sample/formal-mmwave-v1-clean` | `archive/20260826/retired/sample-formal-mmwave-v1-clean` | `4af812701d2814b948c8320ab64a5a14bcce76e7` |

## Held and retained branches

- `docs/rs6240-firmware-multichannel-plan-20260825` is held because it is the head of open PR #1. Its retirement tag `archive/20260826/retired/docs-rs6240-firmware-multichannel-plan-20260825` points to `53c5814e518ebb43a6288860591f3f44feb17abd`.
- `main`, `master`, `chatgpt/multimodal-results-nir-diagnostic-20260826`, `codex/focuswave-mainline-restructure-v1`, `codex/local-analysis-library-canonicalization-20260826`, and `sol/scientific-review-20260826` remain protected by Stage 2B scope.
- `vendor/attention-amd-DirectML` and `vendor/attention-nvidia-cuda` remain because they are vendor branches outside the 32-row retirement matrix and were not in the approved deletion scope.

## Rollback and verification state

- `master` remains at `96525b19422b34291e4d87747fef214d1fec60d7`.
- `legacy/mmwave-hrv-master-pre-focuswave-20260826` remains an immutable rollback tag to that exact SHA.
- No archive or legacy tag was deleted or force-moved.
- Default branch remains `main`; a fresh-clone validation is required after this ledger commit and is recorded in the handoff result.
