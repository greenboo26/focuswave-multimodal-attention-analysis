# FocusWave Stage 2C execution status

## Current state

- Main cleanup commit: `f03bd30a4bf6f1504c56e5c165f388e983493979`.
- Pre-cleanup recovery tag: `archive/20260826/pre-stage2c-main` -> `579f6abcefc86363f62b8abccbac85e87d1a14e8`.
- 57 `LEGACY_PROVENANCE_ONLY` scripts with 97 absolute-path hits were removed from the browsable main tree; no script contents were normalized.
- Three governance branches were archived and deleted after live-ref verification.
- The final repository baseline tag is intentionally not created yet.

## PR closure blocker

PR #1 and PR #2 were read from the live repository and both remain open and unmerged. GitHub read operations succeeded, but the available write endpoint returned HTTP 403 for both comment and `state=closed` updates. Because the required sequence is curated successor -> close PR -> delete PR head, neither PR head branch was deleted.

| PR | head | base | state | disposition |
|---|---|---|---|---|
| #1 | `docs/rs6240-firmware-multichannel-plan-20250825@53c5814e518ebb43a6288860591f3f44feb17abd` | `master` | open | curated hardware successor present; close pending GitHub write access |
| #2 | `chatgpt/multimodal-results-nir-diagnostic-20260826@0e756b275fd9cbbc7d7564531d3200425bf3be23` | `main` | open | curated diagnostic successors and archive tag present; close pending GitHub write access |

The PR bodies and scientific content were not merged. The curated successors are:

- `docs/archive/hardware/RS6240_FORMAL_FIRMWARE_MULTICHANNEL_PLAN_20250825.md`
- `results/supporting/LU_YIMIN_V3_4_1_ECG_RSP_REFERENCE.md`
- `results/engineering_reference/nir/NIR_FEATURE_CONTRACT_DIAGNOSTIC_V2.md`
- `docs/archive/superseded/PR2_MULTIMODAL_STATUS_REFERENCE_20260826.md`

## Vendor discrepancy

The remote no longer contains `vendor/attention-amd-DirectML` or `vendor/attention-nvidia-cuda`. Local tracking/reflog evidence shows these were temporary mirrors fetched from `kyandi233-dev/Attention-Analysis`; the authoritative external refs remain NVIDIA `36a2d596c55b93071a8b5c80459a56c876c06351` and AMD `d8e721079461ef7f71fafcd3edf819858fabbb16`. They are `NON_CANONICAL_VENDOR_MIRROR / NOT_REQUIRED` and were not recreated.

## Gate

`FOCUSWAVE_CUTOVER_STAGE2C = BLOCKED_ON_PR_CLOSURE_API`

No final `focuswave-repository-cutover-v1` tag is created until PR closure and PR-head deletion are completed and the final fresh-clone gate is rerun.
