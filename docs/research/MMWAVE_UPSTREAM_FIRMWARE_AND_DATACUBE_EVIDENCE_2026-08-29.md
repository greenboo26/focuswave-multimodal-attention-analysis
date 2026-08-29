# mmWave upstream firmware and DataCube evidence — 2026-08-29

Status: `ACTIVE / FORMAL-MODE-CLOSED / DETAIL-BOUNDARIES-OPEN`

Purpose: prevent already-completed RS6240 firmware/manual/DataCube investigations from being forgotten and reclassified as wholly unknown. This file records facts already established in prior project audits, separates them from still-unbound SDK/manual details, and records the evidence-relink and line-by-line audit result.

## 1. Already established project facts

### U1 — Formal stored data are not raw ADC

Status: `CONFIRMED_BY_OUTPUT_SEMANTICS`

- The formal stored `ReportDataCube1D` is complex range-domain data with 8 channels.
- Project shape semantics are `frame × range-bin × 8 complex channels`.
- Therefore a range-domain transform has already happened upstream before the downstream Python physiology/QC analysis.
- Downstream code must not treat `ReportDataCube1D` as raw ADC or apply a second range FFT under that assumption.

Scientific consequence: literature steps before the range-domain cube cannot all be audited only from downstream Python; they must be traced to the RS6240 producer/firmware/SDK path.

### U2 — Range FFT is already upstream of `ReportDataCube1D`

Status: `CONFIRMED_BY_OUTPUT_SEMANTICS / PROJECT_EVIDENCE`

- The current canonical project treats `ReportDataCube1D` as already range-FFT-domain complex data.
- This is not an `UNVERIFIABLE_UPSTREAM` item anymore.
- The unresolved question is the exact implementation and parameterization of that upstream transform, not whether a range transform occurred at all.

### U3 — Formal distance spacing is 0.037 m/bin

Status: `CANONICAL_CONFIRMED`

- Current formal RS6240 DataCube distance spacing is `0.037 m/bin`.
- Historical downstream use of `0.08 m/bin` was wrong.
- Correcting only this distance semantics materially changed target/channel selections and the QC crosswalk.
- Canonical evidence: `docs/canonical/MMWAVE_CURRENT_STATE_2026-08-29.md`.

Scientific consequence: any upstream/manual/SDK reconstruction must be consistent with the 0.037 m/bin formal spacing and must not silently revive 0.08 m/bin.

### U4 — Formal firmware image identity was previously audited

Status: `PRIOR_AUDIT_CONFIRMED_NEEDS_PRIMARY_RELINK`

Previously recorded project audit fact:

- firmware image: `mrs6240_p2512.img`
- SHA-256: `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`
- recorded build time: `2026-07-24 21:33:39`

Boundary: the prior audit did **not** establish a complete one-to-one mapping from this exact binary image to a full source-tree Git commit/build manifest. Therefore SDK/default implementation behavior must not automatically be asserted as exact formal-firmware behavior unless the path is tied back to this image or verified from output semantics.

This fact must be re-linked to the original local audit artifact/manual/firmware evidence in the current line-by-line audit; it must not be discarded and rediscovered from zero.

### U5 — Formal image mode and DataCube path are now primary-relinked

Status: `CONFIRMED_IN_FORMAL_FIRMWARE`

The recovered prior audit `2026-08-29_FORMAL_FIRMWARE_RUNTIME_MODE_AUDIT.md` is bound to the local SDK assets. The formal image `mrs6240_p2512.img` has SHA-256 `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`; the adjacent ADC experiment image has SHA-256 `bc3395113a8647f1ec16c779b6b3f153e43a979727d3f1853506ef5548d447d7`. The saved binary comparison identifies `range_resolution_mm=37`, `range_fft_len_log2=8`, and formal `fft_mode=2`, while the ADC experiment has `fft_mode=0`. `radar_framework.h:68-70` defines the enum and `ReportDataCube1D/src/main.c:65-83` binds it into the application configuration. This establishes the formal image as 1D Range-FFT output with no Doppler FFT in the 1D frame; `0xC2` is the complex16 report transport.

The exact formal session burn/boot receipt is still absent. Lower-layer windowing, IQ/channel calibration, physical Tx/Rx timing and compensation, and amplitude scaling therefore remain bounded rather than inferred from generic SDK behavior.

## 2. What is NOT wholly unknown anymore

The following classifications are now prohibited:

- `Range FFT = UNVERIFIABLE_UPSTREAM`
- `ReportDataCube1D data domain = UNKNOWN`
- `range spacing = UNKNOWN`

Correct current interpretation:

| Stage/fact | Current status | What remains to verify |
|---|---|---|
| Raw ADC availability in formal stored dataset | `NOT_PRESENT_IN_FORMAL_STORED_OUTPUT` | producer/firmware source path only |
| Range-domain transform before DataCube | `CONFIRMED` | exact FFT/window/length/zero-padding/cropping implementation |
| ReportDataCube1D complex 8-channel range-domain semantics | `CONFIRMED` | exact channel physical mapping / Tx-Rx ordering |
| Formal range spacing | `CONFIRMED_0.037_M_PER_BIN` | bind to exact firmware/manual parameter derivation |
 | Firmware binary identity | `CONFIRMED_IN_FORMAL_FIRMWARE` | device burn/boot receipt and full build manifest remain absent |

## 3. Still unresolved upstream details

These are the genuine upstream audit questions. They must not be collapsed into a generic “unknown upstream” label.

1. ADC/IF DC-offset removal before range transform: exact implementation, axis, and parameters.
2. Static-clutter/background suppression before or during producer output generation.
3. ADC windowing before FFT: window type and application axis.
4. Exact FFT length and whether zero-padding is used.
5. Exact beat-frequency/range conversion and any near/far bin cropping.
6. Chirp aggregation: single chirp, coherent averaging, noncoherent averaging, zero-Doppler extraction, or another mechanism.
7. Doppler processing before `ReportDataCube1D`, if any.
8. Normalization/scaling of complex range bins.
9. Antenna/channel calibration actually applied to the formal output path.
10. Physical mapping and order of the 8 complex channels, including Tx/Rx identity and timing assumptions.
11. Whether any phase correction/calibration is already applied upstream.

For each item, final status must be one of:

- `CONFIRMED_IN_FORMAL_FIRMWARE`
- `CONFIRMED_BY_OUTPUT_SEMANTICS`
- `SUPPORTED_BY_OFFICIAL_SDK_OR_MANUAL_ONLY`
- `PRIOR_AUDIT_CONFIRMED_NEEDS_PRIMARY_RELINK`
- `UNRESOLVED`
- `NOT_APPLICABLE`

Do not use `UNVERIFIABLE_UPSTREAM` as a blanket status when official manuals/SDK/firmware audit evidence already exists.

## 4. Evidence hierarchy for upstream binding

Use this order when closing each upstream field:

1. exact formal firmware image/build artifact tied to the experiment;
2. matching build manifest/source tree/configuration;
3. official RS6240 SDK source implementing the exact report path;
4. official RS6240 manual/API/report-format documentation;
5. formal output semantics and numerical consistency checks;
6. historical project notes as provenance only.

A lower layer may support a conclusion, but must not overwrite a contradictory higher layer.

## 5. Required recovery task — do not restart discovery from zero

The next audit agent must first recover the **existing** prior firmware/manual/SDK investigation and bind it into the current canonical audit. It should not begin by re-searching generic FMCW literature.

Required outputs:

- exact local/GitHub path(s) of the previous firmware inspection notes;
- official manual/SDK file names, versions, page/section/function references already inspected;
- exact evidence for `ReportDataCube1D` generation semantics;
- exact evidence for range FFT/window/FFT length/chirp aggregation/calibration if previously established;
- exact remaining gaps that truly were not established;
- a corrected upstream stage matrix replacing blanket `UNVERIFIABLE_UPSTREAM` labels.

## 6. Decision

`DECISION U-20260829-01`:

The project must **reuse and bind prior RS6240 firmware/manual/SDK findings before any new upstream investigation**. Already-established facts are project evidence and cannot be reset to unknown merely because they were previously left in scattered notes or chat.

`DECISION U-20260829-02`:

Issue #16 remains paused. The immediate task is evidence recovery + source binding + line-by-line producer/downstream audit, not new model fitting or new mmWave algorithm development.
