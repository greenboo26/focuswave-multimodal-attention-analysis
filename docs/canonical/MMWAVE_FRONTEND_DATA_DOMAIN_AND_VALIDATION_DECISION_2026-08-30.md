# mmWave frontend data-domain, selector, distance, window and HRV validation decision — 2026-08-30

Status: `CANONICAL_CORRECTION / MAIN-BOUND / TASK_MAP_FROZEN`

This document records the 2026-08-30 correction of several previously over-broad interpretations about mmWave preprocessing, target switching, distance gating, VMD dependency handling, 20 s/60 s windows and HRV. It is the detailed methods/decision companion to `MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md`. Future agents must use this document instead of reconstructing these decisions from chat.

## 1. Material corrections made in this review

1. **A higher bin/channel switch rate is not, by itself, evidence that a selector is worse.** If the participant truly moves, a correct tracker should move. The 335-window slow-time complex-mean subtraction A/B therefore demonstrates a material change in selector behavior, not proof of physiological degradation. Extra switching could represent instability, exposure of noise/multipath after removal of a stable complex component, or genuine target motion. Independent motion/placement evidence was not available in that A/B, so the cause is `AMBIGUOUS`.
2. The 335-window intervention was **not preprocessing before the Range FFT**. The archived inputs used by the current producer are already complex range-domain arrays. The intervention subtracts the slow-time complex mean from those range-domain values before the existing selector.
3. Issue #25's controlled 20 s versus trailing 60 s comparison is **not invalid because of different selector/path logic**. The report explicitly reused the same historical fixed target and the same v3.1.1 bandpass/periodogram/peak/course chain while changing the trailing duration. Its result is still only `DIAGNOSTIC_ONLY / UNRESOLVED` because it is a limited targeted comparison and 20 s was never a formal physiological window.
4. `PHYSICAL_GATE_UNRESOLVED` does **not** mean “use no range constraint”. A broad physical region of interest (ROI) that excludes impossible regions such as another room can be scientifically justified from independent geometry/protocol/hardware. What remains unresolved is a narrow physiology-valid interval such as historical 0.30–1.50 m if that interval is justified only by outcome performance rather than independent placement evidence.
5. VMD software provenance is now frozen to `sktime.libs.vmdpy.VMD`; standalone `vmdpy` is historical only. On 2026-08-30 the assistant directly changed `requirements.txt` on `main` from `vmdpy>=0.2` to `sktime==1.1.0` in commit `7513dbe9d7c2fe0d168bb70cffd88de855965924`. The remaining `_load_vmd()` source-level silent fallback removal and tests require a bounded local code edit and are assigned below; do not claim that source patch completed until its mainline commit exists.

## 2. Data-domain taxonomy: raw ADC versus FocusWave archived complex range cube

### 2.1 Raw FMCW ADC / beat-signal domain

A conventional FMCW radar first records ADC samples inside each chirp. A typical logical layout is approximately:

`frame × chirp × RX(or virtual antenna) × fast_time_sample`

Within a chirp the fast-time samples contain the beat signal. Its frequency is related to target range. Operations that genuinely belong to this pre-Range-FFT domain include:

- ADC/IF DC removal and clipping checks;
- I/Q calibration when raw quadrature samples and calibration information are available;
- a fast-time window such as Hamming or Blackman-Harris;
- the 1-D Range FFT itself;
- hardware-specific FFT scaling and range calibration.

Texas Instruments' processing documentation explicitly describes `ADC data -> Range FFT -> radarCube`; TI's current RangeProc implementation also documents a Blackman window before Range FFT in the supported configuration. These operations cannot be reproduced identically by multiplying already-created range bins by a Hamming/Blackman-Harris vector after the FFT.

### 2.2 Range-domain complex DataCube

After Range FFT, each range bin has a complex value `I + jQ`. A typical logical representation for vital-sign work is approximately:

`slow_time/frame × range_bin × channel`

Across slow time, the phase of a plausible target range bin changes with sub-wavelength chest motion. At this stage scientifically compatible operations include:

- slow-time complex centering or background estimation per range-bin/channel;
- MTI/high-pass/recursive static-clutter suppression, if the chosen implementation preserves the vital-sign band;
- range-domain candidate/CFAR/ROI selection;
- block-local target continuity diagnostics;
- phase extraction/unwrapping and displacement conversion;
- respiratory/cardiac filtering, VMD or other post-selection separation;
- spectral and beat estimation.

AoA/beamforming is not automatically available merely because multiple channels exist. It additionally requires known antenna identities/geometry, coherent phase relationships and relevant calibration/provenance.

### 2.3 Current FocusWave producer input domain

`process_vital_signs_v3_1_1.py` loads the stored `tx*` arrays from NPZ, stacks them as complex64, and `_as_range_cube()` returns those complex arrays directly. There is no Range FFT in the current producer. Therefore:

`CURRENT_ARCHIVED_PRODUCER_INPUT_DOMAIN = RANGE_DOMAIN_COMPLEX`

The exact upstream SDK/acquisition path that created those `tx*` arrays, including whether any pre-FFT ADC representation or exact Range-FFT window/scaling/calibration metadata was retained, must be recovered from acquisition/source provenance before making claims about which pre-FFT operations can be replayed. Until that audit is complete:

`ORIGINAL_PRE_RANGEFFT_DATA_AVAILABILITY = TO_VERIFY`

Do not infer “raw ADC never existed”; do not pretend unavailable raw-domain processing can be reconstructed from range-domain NPZ.

## 3. What DC offset means and why it can corrupt vital-sign phase

At one selected range bin/channel, a useful simplified complex signal is:

`z(t) = C_static + s_vital(t) + noise(t)`

where `C_static = I0 + jQ0` is an approximately constant/slowly varying complex contribution and `s_vital(t)` is the tiny cardiopulmonary modulation. `C_static` can include several physically different sources: stationary objects/body parts in the same finite range/angular cell, TX-RX coupling/direct leakage, mixer/local-oscillator leakage, circuit DC terms, and other static clutter. These sources must not be conflated merely because their mathematical effect resembles a complex offset.

Phase is obtained from:

`phi(t) = arg(z(t)) = atan2(Q(t), I(t))`

If the wanted cardiopulmonary component traces a small arc/circle in the I-Q plane but a large static vector displaces that trajectory away from the origin, `atan2(Q,I)` no longer gives the wanted micro-motion angle cleanly. The phase can be compressed or nonlinearly distorted, and motion/noise can produce unstable unwrapping. Peer-reviewed FMCW vital-sign studies therefore treat unwanted DC/static-reflector contribution as a phase-demodulation problem and evaluate complex-plane centering/circle-fitting or related calibration methods.

Important distinction: simple subtraction of the sample mean of I and Q is only one DC/static-clutter strategy. At mmWave, published comparisons have found geometric circle fitting preferable in some settings; slow DC drift can also make one fixed mean inadequate. This is one reason the FocusWave mean-subtraction A/B cannot be generalized to “DC calibration does not work”.

## 4. Translation of a common reference processing chain

A common radar chain can be translated as:

`MTI/static clutter removal -> Range FFT -> spatial localization/beamforming -> phase -> vital signs`

= **动目标指示（MTI）/静态杂波抑制 → 距离向 FFT（把 fast-time 拍频变成距离 bin）→ 空间定位/波束形成（利用多天线在方向上分离目标）→ 从目标复数 I/Q 提取相位/微位移 → 估计呼吸、心率、逐搏时间或 HRV。**

This ordering is illustrative, not universal. TI documents static clutter processing as a `radarCube -> radarCube` operation after Range FFT, and vital-sign papers often subtract slow-time range-bin means after range processing. Therefore every literature method must first be mapped to its required input domain instead of copying a diagram literally.

### Current FocusWave downstream chain

The currently audited v3.1.1 route is closer to:

`stored complex range-domain NPZ`
`-> range/channel power accumulation`
`-> candidate bin/channel scoring (power + HR/BR spectral evidence + phase stability)`
`-> target/channel selection`
`-> selected-bin complex phase unwrap -> displacement`
`-> BR detrend/diff/moving-mean/bandpass candidate logic`
`-> HR bandpass and, when method=vmd_heart, windowed VMD separation`
`-> periodogram + peak candidates`
`-> time/frequency/continuity fusion`
`-> HR/BR summaries + QC`

The key gap versus raw-ADC reference pipelines is that the current archived producer begins **after** the Range-FFT boundary.

## 5. Hamming / Blackman-Harris before Range FFT

An FFT observes a finite record. If a beat sinusoid does not contain an integer number of cycles in the sampled chirp, a rectangular truncation spreads its energy across neighboring FFT bins. This is **spectral leakage**. For radar range processing, the sidelobes of a very strong reflector can contaminate adjacent range bins and hide a weaker reflector.

A fast-time window computes approximately:

`RangeSpectrum[k] = FFT(ADC[n] * w[n])`

before target-range selection.

- **Hamming** reduces sidelobes relative to a rectangular window while widening the main lobe moderately.
- **Blackman-Harris** suppresses sidelobes more strongly but widens the main lobe more, reducing the ability to separate very close targets and changing coherent gain/amplitude.

Thus window choice is a resolution-versus-sidelobe trade-off, not a free improvement. TI's RangeProc documentation provides a concrete example of applying Blackman before Range FFT.

Crucially, `window -> FFT` is not equivalent to taking an already-FFT'd range cube and multiplying its range bins by that window. Consequently, this is only a candidate for FocusWave if the upstream acquisition audit proves the relevant raw/fast-time data or firmware range-processing configuration can be recovered/reproduced.

## 6. Correct interpretation of the frozen 335-window preselection A/B

Frozen A/B:

- A: current range-domain mean-power profile and current v3.1.1 selector;
- B: slow-time **complex mean subtraction on the already range-domain cube**, followed by the same selector/path logic.

Observed:

- candidate availability: 335/335 in both;
- HR selected below 0.30 m: 36.1194% -> 24.1791%;
- HR bin switch: 50.1529% -> 58.4098%;
- HR channel switch: 48.3180% -> 55.6575%;
- BR selected below 0.30 m: 7.1642% -> 7.4627%;
- BR channel switching also increased.

### Corrected interpretation

Do **not** write “B is worse because switching increased”. The valid conclusion is:

`B materially changes target-selection behavior and reduces near-side HR selections, but it does not establish that the extra switches are correct or incorrect.`

Plausible explanations for increased switching are hypotheses, not established causes:

1. removing a stable complex component can reduce winner/runner-up score margins, so noise/multipath components exchange rank more often;
2. dynamic components that were hidden beneath a strong static component become relatively more prominent;
3. real participant/posture movement could become easier to follow;
4. the simple global/within-window mean can itself distort a nonstationary wanted I-Q trajectory or remove part of the useful low-frequency component.

The A/B lacked independent per-window movement/placement truth, so it cannot distinguish these explanations. Therefore the current decision remains `DO_NOT_PROMOTE_THIS_MEAN_SUBTRACTION`, but the rationale is **insufficient validated benefit / ambiguous switching correctness**, not “low switching is intrinsically better”.

## 7. Historical front-end/preprocessing work: what is known and what is not

Repository history shows more than one earlier signal-processing exploration. The historical mmWave method matrix/failure registry records work involving VMD, SSA/VMD, adaptive notch/harmonic handling, multi-bin/channel approaches and a historical `scripts/experiment_*.py` family including CEEMDAN, Hampel, phase-difference, CFAR, envelope and SPC-style alternatives. Some historical exact parameter/result tables are incomplete, so those items are evidence/provenance rather than automatically reusable validated methods.

The 335-window slow-time complex-mean subtraction run is currently the strongest **same-denominator controlled pre-selector front-end A/B** in the current evidence chain. No current canonical evidence has established that FocusWave previously ran a controlled **raw-ADC pre-Range-FFT Hamming/Blackman-Harris** A/B. Task T1 below must recover exact historical scripts/commits and classify each method by input domain and evidence rather than repeating them.

## 8. How to compare preprocessing/selector methods without tuning to ECG MAE

ECG/RSP reference remains essential for final physiological validation, but it must not be used to repeatedly tune every front-end parameter on the same subjects. The formal comparison hierarchy is:

### Stage A — physics/data-domain gate

A candidate is considered only if:

- its required input domain exists;
- it targets a documented failure mechanism (static clutter/DC drift/multipath/target ambiguity, etc.);
- its core parameters come from hardware/protocol/literature or a prespecified rule, not from searching for minimum ECG error.

### Stage B — upstream selector/front-end evaluation, with parameters frozen before ECG scoring

Use fixed windows and report at least:

- candidate availability and explicit failure rate;
- broad physical-ROI compliance;
- winner-versus-runner-up score margin / target confidence;
- block-local trajectory continuity **without treating switch count as the objective**;
- implausible target jumps in bins/meters per unit time;
- phase stability / circular dispersion / unwrap-jump rate;
- dynamic-to-static or target-to-background contrast;
- neighborhood/channel consistency;
- agreement with independently synchronized posture/motion evidence when available (e.g. RGB head/body motion or protocol block reset), without using ECG to decide target location.

### Stage C — frozen-path held-out physiology validation

Only after the candidate method and selector/path are frozen, validate on held-out participants against ECG/RSP. Report HR/BR MAE, median AE, bias, Bland-Altman limits, coverage/failure and participant/session distributions. Correlation is secondary because a high correlation can coexist with large bias.

A practical bounded study may compare **current baseline + at most two physically justified/reusable candidates**, with a prespecified primary decision rule. The final held-out cohort is for validation, not for selecting thresholds.

## 9. Distance control: broad physical ROI versus narrow physiology-valid gate

FocusWave does need protection against impossible/far targets. The mistake is not using a distance constraint; the mistake is deriving a narrow interval from whichever range makes HR error look best.

### Broad physical ROI — justified and recommended

Define a coarse region using independent information such as:

- radar installation position and orientation;
- expected chair/participant chest region;
- room dimensions, wall/adjacent-room geometry and occlusions;
- calibrated 0.037 m/bin spacing and any range bias;
- sensor useful range/FOV and acquisition protocol;
- plausible posture/slouch/reposition tolerance.

The broad ROI should contain every physically plausible participant position while excluding impossible locations such as >10 m/behind walls/another room. Near boundaries, a soft prior can be preferable to an arbitrary hard cutoff if placement uncertainty is substantial.

### Narrow physiology-valid gate — still unresolved

Historical 0.30–1.50 m remains `HISTORICAL_GATE_SENSITIVITY`. It cannot be called a validated physiological gate without independent placement/calibration evidence. The correct next task is to recover room/device/seat geometry and, if available, acquisition photographs/measurements or calibration-target data. ECG outcome must not be used to select the ROI.

## 10. 20 s versus 60 s: corrected evidence boundary

20 s first entered the current targeted-validation chain as an engineering diagnostic for block-local continuity / ECG-aligned comparison: `20 s window / 10 s step / 5 s boundary guard`. The preceding block-reset/marker-alignment contract did not provide a physiological argument that 20 s is an optimal HR window. Therefore:

`20S = HISTORICAL_DIAGNOSTIC_ONLY`

Issue #25 later ran a legitimate controlled duration comparison: same historical fixed target, same v3.1.1 bandpass/periodogram/peak/course chain and same alignment; only trailing duration changed. On 283 common ECG-valid comparisons, 60 s had lower descriptive error than 20 s (20 s MAE 14.703 bpm; 60 s MAE 5.609 bpm; 60 s better in 208 pairs, 20 s in 74, one tie). That is useful evidence but not a final formal-window decision because the test used only the targeted sessions/blocks and remains conditional on the current selector/data-quality limitations.

Other durations are separate contracts and must not be conflated:

- 25 s: internal v3.1.1 HR time-course estimation;
- 40 s with 20 s step: windowed VMD decomposition;
- 60 s: historical trailing probe-level HR aggregation;
- `pre_30s`: current **multimodal probe-alignment window**. It does not automatically dictate the internal physiological estimator duration.

After the selector/path is frozen, Task T4 must reconcile estimator duration with frequency resolution, stationarity, block/probe semantics and held-out reference validity. Do not re-run 20 s merely because it exists historically.

## 11. What it means to prove `radar beats ≈ ECG R-peaks`

HRV requires valid beat timing, not merely an average HR close to ECG. The formal beat gate must be prespecified and participant-disjoint:

1. synchronize each formal block using experiment markers + Biopac digital pulses + audited mmWave Unix timestamps; retain alignment residuals;
2. obtain ECG R-peaks with an independently validated ECG detector/QC;
3. extract radar beat timestamps **without using ECG timestamps to tune the radar detector**;
4. perform one-to-one matching, primary tolerance prespecified (current audit uses ±75 ms) with a wider tolerance such as ±150 ms only as sensitivity; one ECG/Radar beat cannot be reused;
5. report TP/FN/FP, sensitivity/recall, precision, F1, matched timing bias, median absolute timing error and p95 error by participant/block/window;
6. form paired consecutive intervals only where adjacent radar beats and adjacent ECG R-peaks are validly matched; compare radar IBI to ECG R-R interval with coverage, MAE/bias and Bland-Altman analysis;
7. inspect failure modes: missed beats, extra peaks, harmonic locking, synchronization errors and weak-signal intervals;
8. calculate RMSSD/SDNN only after a prespecified beat-level gate passes. Standard short-term HRV uses approximately 5 min as the conventional comparator; any ultra-short RMSSD/SDNN must be separately validated against an appropriate longer criterion. Frequency-domain HRV has stricter duration/stationarity requirements.

Current FocusWave evidence fails before Step 8: ±75 ms matching produced sensitivity ~0.170 and precision ~0.211; even ±150 ms yielded only ~0.359/~0.444. Therefore `HRV/IBI = BLOCKED / EXCLUDE` remains unchanged.

## 12. VMD software correction status

Formal software decision:

- `VMD_BACKEND = sktime.libs.vmdpy.VMD`
- `sktime == 1.1.0`
- standalone `vmdpy == 0.2` = `HISTORICAL_REFERENCE_ONLY`
- silent backend fallback = forbidden.

Direct mainline modification by the assistant:

- commit `7513dbe9d7c2fe0d168bb70cffd88de855965924`
- message `fix(mmwave): pin maintained sktime VMD backend`
- `requirements.txt`: removed `vmdpy>=0.2`, added `sktime==1.1.0`.

The current large producer file still contains the historical `_load_vmd()` fallback and therefore requires one narrow local source patch. This is not a new scientific-analysis task; it is a reproducibility implementation correction. Task T0 gives the exact bounded change and acceptance criteria. Formal VMD runs must not be launched until T0 source/test closure is committed to current `main`.

## 13. Frozen task map through the step immediately before multimodal integration

No new long-lived mmWave branch is authorized. Each task starts by fetching current `origin/main`; if another agent advanced it, integrate on the latest main rather than replaying an old SHA.

### T0 — software reproducibility closure (`#29`, local Codex code task)

Input baseline: current `main` after assistant commit `7513dbe...`.

Required changes:

- patch `scripts/process_vital_signs_v3_1_1.py::_load_vmd()` to import only `sktime.libs.vmdpy.VMD`;
- use `importlib.metadata.version("sktime")` and require `1.1.0` for the frozen formal environment; import/version mismatch must raise an explicit error and must never import standalone `vmdpy`;
- persist backend/package/version plus VMD parameters (`K`, alpha, tau, init, tol, window/step) in the result/config/provenance object or formal run manifest;
- add regression tests proving that standalone `vmdpy` cannot become a fallback and that version mismatch fails explicitly;
- run an isolated parity/smoke audit with old standalone `vmdpy==0.2` only in a comparison environment: representative even-length frozen signals, odd-length signal and zero/near-zero pathological signal; compare mode/omega output, selected downstream heart mode/HR where applicable and runtime. This audit is provenance evidence, not permission to restore the old backend;
- update `PROJECT_STATUS.md`, `ANALYSIS_HISTORY_LEDGER.md` and this canonical document with the completed main SHA;
- delete the truly redundant remote ref `codex/mmwave-production-contract-review-fix-v1` after verifying it still has zero unique commits: `git push origin --delete codex/mmwave-production-contract-review-fix-v1`;
- leave PR #20 closed/unmerged/[SUPERSEDED] because it contains useful historical proposal provenance.

No new branch. No HR/BR parameter change. No full formal run.

### T1 — acquisition/data-domain + historical preprocessing provenance audit (`#27`)

Recover:

- sensor/SDK/acquisition path that generated `tx*` NPZ arrays;
- whether raw ADC/fast-time samples were retained anywhere;
- exact Range-FFT/window/scaling/DC calibration performed upstream;
- channel/antenna identity, coherence and geometry metadata;
- all prior front-end experiments (CEEMDAN, Hampel, phase diff, CFAR, envelope, SPC, SSA/VMD, notch/harmonic, multi-bin/channel, clutter subtraction) with exact commit/script/parameters/result if recoverable.

Deliver a matrix: `method -> required data domain -> available? -> previously tried? -> evidence/result -> reusable? -> gap`.

### T2 — independent coarse physical ROI contract (`#26`)

Use room/radar/chair/protocol/device geometry, not ECG performance, to define a broad physically plausible range/FOV. Explicitly distinguish hard-impossible space from uncertain boundary space. Do not automatically restore 0.30–1.50 m.

### T3 — bounded front-end / selector A/B (`#27`, only after T1+T2)

Reuse historical implementations where possible. Compare current baseline plus **no more than two** strongest physics-compatible candidates. Freeze parameters before physiology scoring. Primary upstream decision metrics are physical ROI compliance, trajectory plausibility, selector confidence/margin, phase quality, independent motion/posture consistency and failure/coverage; switch rate is diagnostic only. After freezing methods, use participant-held-out ECG/RSP as physiological validation, not parameter tuning.

### T4 — formal HR/BR temporal-window contract (`#25`, after selector/path freeze)

Retire 20 s to diagnostic history. Reconcile internal estimator duration and probe-level aggregation with frequency resolution, stationarity, formal block/probe boundaries and canonical multimodal `pre_30s` alignment. Do not choose duration solely from the targeted MAE table and do not allow windows to cross block/rest boundaries.

### T5 — held-out HR/BR validity gate

With selector/path/window frozen, validate participant-disjoint HR against ECG and BR against RSP: coverage, MAE/median AE, bias/Bland-Altman, participant/session distributions and prespecified failure criteria. HR/BR remain `HOLD / SUPPORTING_ONLY` until this gate passes.

### T6 — beat/HRV validity gate

Run the beat-matching protocol in Section 11. If it does not pass, HRV remains excluded from this project's multimodal predictor block; do not compensate by shopping for new HRV algorithms. If it passes, separately pre-register HRV metric/duration validation.

### T7 — mmWave probe adapter (`#29`, immediately before multimodal integration)

Only after the upstream roles are frozen, adapt existing canonical mmWave outputs to the already-frozen canonical 1,440-probe timeline:

- `formal_multimodal_v2/mmwave/mmwave_probe_merge_ready.csv`
- `mmwave_probe_merge_ready_manifest.json`
- optional aggregate/audit table
- exact key: `repeat_participant_id, session_id, block_id, probe_id, window_name`
- preserve all canonical probe rows and explicit missingness; no zero filling;
- validate schema, non-null/unique keys, row count/coverage and merge behavior;
- HRV fields remain null/excluded unless T6 independently passes;
- only fields permitted by `MMWAVE_FEATURE_CONTRACT_V1.csv` may enter the later contribution model.

`T7 PASS` is the last mmWave-specific step before final multimodal attach/contribution analysis. Do not start the final multimodal model before it.

## 14. External method references used for this correction

- Texas Instruments, mmWave SDK User Guide: ADC -> Range FFT -> radarCube; static-clutter DPU operates on radarCube. https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/1023/6266.mmwave_5F00_sdk_5F00_user_5F00_guide.pdf
- Texas Instruments, current RangeProc documentation: Blackman window before Range FFT in the documented configuration. https://software-dl.ti.com/ra-processors/esd/MMWAVE-L-SDK/05_05_00_02/exports/api_guide_xwrL64xx/RANGEPROC_PAGE.html
- Paterniani et al., analysis of DC-offset calibration in FMCW/mmWave vital-sign monitoring. https://pmc.ncbi.nlm.nih.gov/articles/PMC9781610/
- Remote Monitoring of Human Vital Signs Based on 77-GHz mm-Wave FMCW Radar: I/Q DC offset and dynamic DC correction before phase extraction. https://pmc.ncbi.nlm.nih.gov/articles/PMC7285495/
- Respiration and Heart Rate Monitoring in Smart Homes: slow-time static-clutter mean removal after range-bin representation. https://pmc.ncbi.nlm.nih.gov/articles/PMC11054141/
- Esco & Flatt, ultra-short lnRMSSD versus conventional 5-min criterion. https://pmc.ncbi.nlm.nih.gov/articles/PMC4126289/

## 15. Governance rule

Any later change to input-domain interpretation, ROI/gate, front-end candidate, selector/path, window contract, beat gate, VMD backend or multimodal eligibility must update this document and `MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md` in the same mainline work cycle, with exact evidence commit/run. Chat-only decisions are non-authoritative.