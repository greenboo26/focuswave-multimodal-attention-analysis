# FocusWave Stage 2C execution status

## Current state

- Main cleanup commit: `43cd21a271c67856c98ef69d9a5e08bf7061fbbf`.
- Pre-cleanup recovery tag: `archive/20260826/pre-stage2c-main` -> `579f6abcefc86363f62b8abccbac85e87d1a14e8`.
- 57 `LEGACY_PROVENANCE_ONLY` scripts with 97 absolute-path hits were removed from the browsable main tree; no script contents were normalized.
- Three governance branches were archived and deleted after live-ref verification.
- The final repository baseline tag is created only after the final fresh-clone validation described below.

## PR closure blocker

PR #1 and PR #2 were read from the live repository, closed without merge, and their head branches were deleted only after successor/archive verification. An intermediate GitHub write response returned HTTP 403, but a subsequent live read confirmed the resulting closed state.

| PR | head | base | state | disposition |
|---|---|---|---|---|
| #1 | live branch `docs/rs6240-firmware-multichannel-plan-20260825@53c5814e518ebb43a6288860591f3f44feb17abd` | `master` | closed, unmerged | GitHub PR metadata displayed the date-suffixed head as `20250825`; live remote ref was `20260825`; curated hardware successor present; actual live head deleted; retirement tag retained |
| #2 | `chatgpt/multimodal-results-nir-diagnostic-20260826@0e756b275fd9cbbc7d7564531d3200425bf3be23` | `main` | closed, unmerged | curated diagnostic successors present; head branch deleted; archive tag retained |

The PR bodies and scientific content were not merged. The curated successors are:

- `docs/archive/hardware/RS6240_FORMAL_FIRMWARE_MULTICHANNEL_PLAN_20250825.md`
- `results/supporting/LU_YIMIN_V3_4_1_ECG_RSP_REFERENCE.md`
- `results/engineering_reference/nir/NIR_FEATURE_CONTRACT_DIAGNOSTIC_V2.md`
- `docs/archive/superseded/PR2_MULTIMODAL_STATUS_REFERENCE_20260826.md`

## Vendor discrepancy

The remote no longer contains `vendor/attention-amd-DirectML` or `vendor/attention-nvidia-cuda`. Local tracking/reflog evidence shows these were temporary mirrors fetched from `kyandi233-dev/Attention-Analysis`; the authoritative external refs remain NVIDIA `36a2d596c55b93071a8b5c80459a56c876c06351` and AMD `d8e721079461ef7f71fafcd3edf819858fabbb16`. They are `NON_CANONICAL_VENDOR_MIRROR / NOT_REQUIRED` and were not recreated.

## Gate

`FOCUSWAVE_CUTOVER_STAGE2C = READY_FOR_FINAL_SMOKE_AND_BASELINE_TAG`

The final `focuswave-repository-cutover-v1` tag must point to the exact `main` SHA that passes the final fresh-clone gate.
