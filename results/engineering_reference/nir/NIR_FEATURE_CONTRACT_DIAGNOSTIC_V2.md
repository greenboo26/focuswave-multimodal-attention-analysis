# NIR feature contract diagnostic V2

> `ENGINEERING_REFERENCE / PRE-RECOVERY DIAGNOSTIC / NOT_A_FINAL_RESULT`

This curated reference supersedes the NIR feature-contract section of PR #2. It records the contract boundary and diagnostic interpretation without copying participant-level outputs or starting a new production run.

## Current contract

- NVIDIA producer: `kyandi233-dev/Attention-Analysis@nvidia-cuda@36a2d596c55b93071a8b5c80459a56c876c06351`.
- AMD producer: `kyandi233-dev/Attention-Analysis@amd-DirectML@d8e721079461ef7f71fafcd3edf819858fabbb16`.
- NIR v1 feature family: 10 PIR + 10 OAR + 10 QC/coverage fields. Event-level PERCLOS and blink duration are not currently present.
- `69/72` formal fullclass status is unchanged.
- `68 sessions / 44 participants / 1,360 probes` is the pre-recovery NIR v1 boundary, not a final recovered cohort.
- `sub-100` and `sub-178` are `RECOVERABLE_PENDING_FULL_RECOVERY_QC_PROBE_ALIGNMENT`; existing evidence is smoke evidence only.
- `sub-099` remains a `master_timeline` blocker.

## Interpretation boundary

Recovery, QC, and Probe alignment must complete before any affected cohort is rerun under the frozen contract. A small manual blink/PERCLOS feasibility check is a prerequisite for a future NIR v2 decision. This document does not authorize formal multimodal inference.

Source PR head: `0e756b275fd9cbbc7d7564531d3200425bf3be23`; full source is preserved by `archive/20260826/pr2-nir-diagnostic-pre-focuswave`.
