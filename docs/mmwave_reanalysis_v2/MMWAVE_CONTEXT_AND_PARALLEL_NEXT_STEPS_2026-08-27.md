# mmWave context comparison and parallel next steps — 2026-08-27

Status: `PASS_COORDINATION_CREATED`

Branch: `codex/mmwave-formal-reanalysis-v2`

## Why this note exists

The AgeBalanced root-cause audit is complete enough to return to the FocusWave mainline. The purpose of the remaining mmWave work is context and interpretation, not new algorithm fishing.

Current development-only AgeBalanced results under the official ECG FFT reference:

| Route | Input/window | Pooled MAE | Median session MAE | Coverage | Interpretation |
|---|---|---:|---:|---:|---|
| Historical `f4a8c74` | AgeBalanced derived / 25 s | 10.493 | 9.296 | 100% | historical baseline |
| Current project | AgeBalanced derived / 30 s | 10.361 | 8.575 | 100% | current product-aligned comparison route |
| Project route | AgeBalanced derived / 50 s | 9.292 | 7.813 | 100% | longer-window comparison |
| SSA+VMD adapted | AgeBalanced derived / 50 s | 9.012 | 5.253 | 100% | only 0.280 BPM pooled-MAE better than 50 s project; other error metrics do not support a stable advantage |
| Project route | AgeBalanced derived / 60 s | 8.273 | 6.517 | 14 complete sessions only | limited |
| Lei SSA adapted | AgeBalanced derived / 60 s | 8.670 | 7.450 | 14 complete sessions only | limited |

The earlier 26.98–38.06 BPM figures are not used for AgeBalanced HR performance claims because they came from the non-official `ecg_reference_v1` benchmark semantics.

## External context already verified

AgeBalanced (Parralejo et al., Scientific Data 2026, DOI `10.1038/s41597-026-07172-9`) is a 110-participant, 60 GHz FMCW vital-sign dataset with lying/sitting rest and post-exercise conditions, medical Movesense ECG reference, about 50 s recordings, and instructions to remain calm, silent and still. It provides an official simple FFT-based frequency-estimation baseline. This makes it a useful external basic-capability benchmark, but it is easier than FocusWave's real cognitive-task setting because FocusWave includes ongoing attention tasks, button presses, posture drift and natural small movements.

DR-MUSIC (Chen et al., Scientific Reports 2024, DOI `10.1038/s41598-024-77683-1`) reports substantially lower error in its own small controlled experiments, but used six participants in repeated seated-rest measurements at about 0.65 m and Apple Watch reference. Those results are not directly comparable to AgeBalanced MAE or FocusWave because dataset, reference device, sample size and evaluation metric differ.

Lei et al. (Digital Signal Processing 2025, DOI `10.1016/j.dsp.2024.104911`) targets respiratory-harmonic interference using SSA plus VMD-family processing. The project already tested an adapted implementation on AgeBalanced; under the official ECG reference it did not show a stable, practically meaningful advantage over the project route.

## Parallel workstreams

Two AIs should proceed in parallel without creating new remote branches unless explicitly authorized.

### AI-A — external method / scenario comparison

Build a rigorous comparison table for AgeBalanced official baseline, current FocusWave project route, SSA+VMD/Lei, DR-MUSIC, mmHRV and other directly relevant recent methods already cited by the project. For every row verify original source, participant count, radar hardware/frequency, distance, posture/activity, recording length, reference device, metric definition, reported error, motion assumptions, and similarity to FocusWave. Do not compare raw numbers across incompatible metrics without qualification. Output a user-readable interpretation of where the current ~9–10 BPM AgeBalanced result sits relative to the literature.

### AI-B — return to the FocusWave main analysis plan

Recover the current canonical mainline state from repository evidence rather than old chat memory. Do not rebuild cohort/modality tables that already exist. Identify what parts of behavior, probe, questionnaire, RGB, NIR, mmWave, repeated-subject handling, common-sample analysis, multimodal fusion and participant-level model validation are already complete, what is partial, and what is actually next. Reconstruct the earlier competition-time / approximately ten-hour execution plan from durable repository evidence if it exists; if no exact ten-hour artifact exists, state that explicitly and derive the smallest evidence-based continuation from the current canonical status. The next work should advance the mainline, not reopen mmWave HR R&D.

## Guardrails

- Reuse `codex/mmwave-formal-reanalysis-v2` for mmWave documentation work; do not create work/snapshot/backup remote branches.
- Do not touch AgeBalanced held-out 80 for selection/tuning.
- Do not start a new mmWave HR algorithm family.
- Do not touch `J:\Data` physiology or HRV unless a later explicit task authorizes it.
- Do not overwrite unrelated user work.
- Completion claims use `PASS / PARTIAL / BLOCKED`.
