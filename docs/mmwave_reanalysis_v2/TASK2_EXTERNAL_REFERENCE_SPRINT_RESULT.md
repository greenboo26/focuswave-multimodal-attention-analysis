# 毫米波任务2：单一外部参考方案限时比较结果

Status: `BLOCKED`

Run date: 2026-08-27

## Scope actually executed

The task contract was read and applied. The only permitted external route was SSA + VMD / EE-PCC-VMD, using the AgeBalanced development split (30 participants, 60 Rest sessions), 30 s / 5 s windows, `ecg_reference_v1`, and the existing unified benchmark contract. No held-out participant, formal `J:\Data`, BR, HRV, or other candidate family was accessed.

No external development score was generated. The route was stopped at the implementation compatibility gate before any candidate result could influence a decision.

## Reuse and parameter audit

The DSP 2025 paper is the selected primary reference (`10.1016/j.dsp.2024.104911`), but no author implementation was found. It therefore remains `paper_reimplementation`, not an official reproduction. The accessible SSA-VMD paper reports concrete parameters: SSA trajectory window `L=400`; a singular-value reconstruction rule tied to the `0.1*L` position; VMD `K=5`, `alpha=1000`, `tau=0`, `DC=1`, `init=0`, `tol=1e-6`. See the [paper record](https://pmc.ncbi.nlm.nih.gov/articles/PMC9861067/).

The paper uses an approximately 50 s UWB resting signal. The frozen AgeBalanced benchmark supplies a 10 Hz range-FFT-derived signal and exactly 300 samples per 30 s window. The published `L=400` cannot be applied to that input. Replacing it with a smaller embedding dimension, padding to 400, or changing the singular-value reconstruction rank would be a new method rule with no recovered source basis. The task contract explicitly forbids inventing such parameters.

The MIT `vmdpy` component already has a fixed commit and direct-module smoke evidence in the Reuse Gate, but that does not establish the combined SSA+VMD method. The combined adapter remains `NOT_RUN` and has no benchmark output.

## Development comparison

| Route | Coverage | MAE | Median AE | RMSE | Decision |
|---|---:|---:|---:|---:|---|
| Project historical baseline, 30 s / 5 s | 95.5% (256/268) | 26.98 BPM | 13.79 BPM | 41.13 BPM | Existing development baseline |
| SSA + VMD external reference | N/A | N/A | N/A | N/A | `BLOCKED`; no score generated |

The project baseline is far outside the frozen HR gate (coverage 0.80, MAE 5 BPM, median AE 3 BPM, RMSE 8 BPM). No fair claim about improvement, coverage trade-off, or harmonic-lock reduction can be made because the external route never reached a valid adapter.

AgeBalanced has no RSP reference, so respiratory-harmonic lock status remains `NOT_ASSESSABLE`; it must not be reported as zero. No HRV work was performed.

## Recommendation

`DOWNGRADE_PHYSIOLOGY`

This is a product-routing recommendation, not a claim that SSA+VMD performs poorly. The only measured project baseline fails the frozen HR gate, while the single external route cannot be fairly instantiated on the frozen 30 s input without inventing parameters. Keep mmWave motion/phase/quality features as supporting-signal candidates for the multimodal line; do not present HR as a validated physiological output.

`ADVANCE` is not justified because no external development improvement was measured. `KEEP_PROJECT_ROUTE` as a physiological HR route is not justified because the measured baseline is substantially outside the gate.

## Stop boundary and next phase

Task 2 is complete as a bounded compatibility decision. Do not switch to DR-MUSIC, Harmonic MUSIC, NOMP, CEEMDAN, beamforming, or another algorithm family in this task. Do not enter 80-person comparison, RS6240 calibration, or formal `J:\Data` analysis automatically.

The only defensible follow-up for physiology would require a separately authorized external reference whose published input/parameter contract is directly compatible with the frozen 30 s AgeBalanced representation, or a separately approved benchmark-contract revision. Otherwise, time should move to the multimodal AI and psychological measurement mainline.
