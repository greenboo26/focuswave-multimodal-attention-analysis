# mmWave HR / BR / HRV shared-pipeline evidence and project decision

Date: 2026-08-30
Status: EVIDENCE / DESIGN-CONTRACT, not a physiology-validity promotion
Scope: explain how radar HR, BR, and HRV relate in the literature and how that should constrain the FocusWave analysis path. This document does not authorize a new estimator, new gate, ECG-informed tuning, or diagnostic-to-formal promotion.

## 1. Core answer

HR and HRV should not be implemented as two unrelated end-to-end pipelines.

The literature-supported structure is:

1. shared upstream radar sensing and target localization;
2. shared complex phase / chest-motion extraction;
3. respiration and cardiac components are separated into different physiological branches;
4. the cardiac branch recovers heartbeat timing or an equivalent cardiac waveform;
5. once reliable beat times are available, **HR and IBI are obtained from the same beat sequence**;
6. HRV is then calculated from the IBI/RR-interval sequence over a substantially longer analysis interval than a normal short HR window.

Therefore, a successful radar-HRV pipeline intrinsically contains enough information to calculate HR from beat intervals. A separate spectral HR estimator can still be retained as an independent robustness/QC/fallback estimate, but it should not be treated as a scientifically independent requirement if beat-level cardiac timing is already validated.

BR is different: respiration occupies a much lower frequency band and usually needs its own branch because respiratory displacement is much larger than cardiac displacement and can contaminate the cardiac signal through harmonics.

The intended project architecture is therefore:

`shared target / phase extraction -> BR branch + cardiac branch`

and inside the cardiac branch:

`heartbeat waveform / beat times -> IBI sequence -> HR + HRV`

rather than:

`one unrelated HR pipeline + another unrelated HRV pipeline`.

## 2. Direct literature evidence

### 2.1 mmHRV: Contactless Heart Rate Variability Monitoring Using Millimeter-Wave Radio

F. Wang, X. Zeng, C. Wu, B. Wang, K. J. R. Liu, IEEE Internet of Things Journal, 2021. DOI: 10.1109/JIOT.2021.3075167.

This is the most directly relevant millimeter-wave HRV paper located in the current review.

The published description states that mmHRV contains two major upstream components:

1. a calibration-free target detector that identifies each user's location;
2. a heartbeat-signal extractor that decomposes the phase modulated by chest movement and recovers a heartbeat signal.

The exact time of each heartbeat is then estimated from peaks in the heartbeat signal. Inter-beat intervals are derived from successive heartbeat times, and the IBI series is subsequently used to evaluate HRV metrics.

The important architecture is therefore:

`target detection -> phase/chest-motion heartbeat extraction -> heartbeat peak timing -> IBI -> HRV`.

Because HR is mathematically obtainable from the same beat intervals (`instantaneous HR ~= 60 / IBI` and average HR from the interval sequence), the HRV path already contains the information required to compute HR. The paper's scientific emphasis is IBI accuracy rather than only average spectral HR accuracy. Reported median IBI estimation error is 28 ms in the cited evaluation.

Project implication: if FocusWave eventually validates a radar beat sequence against ECG R-peaks, HR can be calculated from those same beat times. We should not build a completely separate second cardiac sensing pipeline solely because one output is called HR and another HRV.

### 2.2 Contactless Radar Heart Rate Variability Monitoring Via Deep Spatio-Temporal Modeling

H. Wang et al., ICASSP 2024, pp. 111-115.

This work is HRV-oriented and treats cardiac rhythm reconstruction as a fine-grained temporal sensing problem rather than an average-HR-only problem. It is another example that HRV requires preserving beat/rhythm information, not merely identifying one dominant heart-rate spectral peak.

Project implication: a periodogram HR estimate alone is insufficient evidence for HRV. The pipeline must preserve or reconstruct beat-level timing/rhythm information.

### 2.3 Radar HRV work using 60 s and 300 s windows

A Doppler-radar HRV validation study explicitly calculated SDNN and RMSSD using non-overlapping 60 s and 300 s windows, with 300 s serving as the longer conventional reference and 60 s examined as a faster alternative.

Project implication: the 20 s FocusWave HR diagnostic window must not automatically become the HRV analysis window. The HR and HRV contracts need different time scales even if they share the same beat-level cardiac signal.

### 2.4 Radar HRV studies using long recordings

More recent FMCW/radar HRV work uses long recordings (for example, multi-minute / 10-minute acquisitions) to derive beat intervals and calculate metrics such as SDNN, RMSSD, and pNN50.

Project implication: long-enough IBI sequences are part of the HRV measurement problem. Short-window HR estimation and HRV are not interchangeable tasks.

### 2.5 ViMo: Multiperson Vital Sign Monitoring Using Commodity Millimeter-Wave Radio

F. Wang et al., IEEE Internet of Things Journal, 2020/2021. DOI: 10.1109/JIOT.2020.3004046.

ViMo is an example of a millimeter-wave vital-sign system that jointly addresses respiration and heart rate. Its purpose is not HRV, but it demonstrates the common shared-upstream / separated-physiology structure used by radar vital-sign systems: localize the person, extract chest-motion information, then estimate respiration and heart-related quantities.

Project implication: BR does not require an entirely separate radar acquisition pipeline. It shares target/chest-motion upstream processing but uses a lower-frequency respiratory branch.

### 2.6 mmRH: Noncontact Vital Sign Detection With an FMCW mm-Wave Radar

L. Liu et al., IEEE Sensors Journal, 2023. DOI: 10.1109/JSEN.2023.3250500.

This work explicitly targets respiration rate and heart rate together. The broader radar literature summarized around mmRH distinguishes two classes of outputs:

- direct HR/RR estimation from filtered/decomposed physiological components;
- more complex cardiac metrics such as HRV, which require a sufficiently accurate heartbeat / IBI representation.

Project implication: HR/BR estimation can be simpler than HRV, but HRV should grow out of the validated cardiac beat representation rather than being bolted onto a short-window average-HR spectrum.

## 3. What 'simultaneously measuring HR, BR, HRV' actually means

The phrase does not normally mean that three fully independent algorithms start from raw radar and never share information.

A technically coherent simultaneous system is closer to the following.

### Stage A — target localization and usable radar signal

Input: complex FMCW / mmWave range-domain data.

Tasks:

- identify the human target / useful spatial channel or range bin;
- reject grossly invalid or non-human regions according to independent physical / signal-quality constraints;
- preserve a stable target trajectory where possible.

Output: a target-associated complex radar time series.

This stage is common to HR, BR, and HRV.

### Stage B — phase / displacement representation

The selected complex radar signal is converted to phase and typically unwrapped/detrended. Chest-wall movement appears as phase/displacement variation.

Output: a chest-motion signal containing strong respiratory motion plus much smaller cardiac motion and interference.

This stage is also shared.

### Stage C — respiration branch

Respiration is low-frequency and generally much larger in displacement than heartbeat motion.

Typical operations include:

- detrending;
- low-frequency respiration band filtering/decomposition;
- respiration peak/frequency estimation;
- quality/consistency checks.

Output: respiration waveform / respiratory cycles / BR.

This branch can also provide useful information about respiratory harmonics that contaminate the cardiac band, but a respiration estimate must not be used as an ECG-informed tuning target.

### Stage D — cardiac-signal separation

The cardiac branch tries to suppress respiration and other interference while retaining the much smaller heartbeat component.

Methods across the literature include band separation, EMD/VMD-type decomposition, harmonic suppression, spatial processing, or learned spatio-temporal reconstruction. The method itself varies by paper; the scientific requirement is that the resulting cardiac timing must be validated rather than assumed from a clean-looking waveform.

Output: cardiac/heartbeat waveform or beat candidates.

### Stage E — heartbeat timing

This is the decisive stage for HRV.

Locate individual heartbeat events:

`t1, t2, t3, ...`

Then calculate:

`IBI_i = t_(i+1) - t_i`.

For HRV, validation must compare radar beat timing / IBI with ECG R-peak timing or an equivalent beat-level reference. A good average HR alone cannot validate this stage.

### Stage F — derive HR from the beat series

Once reliable beat times exist, HR is naturally available from the same sequence.

Examples:

- instantaneous HR: approximately `60 / IBI`;
- mean HR over an interval: based on the average/median IBI or beat count per time.

This is why HRV-capable cardiac sensing already contains HR information.

However, a separate frequency-domain HR estimate can remain valuable as:

- an independent QC signal;
- a fallback when individual beats cannot be resolved;
- a consistency check against beat-derived HR.

It should not become a second unrelated cardiac architecture unless evidence shows that this is necessary.

### Stage G — derive HRV from a longer IBI sequence

HRV is calculated from variation in the IBI/RR series, not from the average HR value.

Examples:

- RMSSD: successive IBI differences;
- SDNN: standard deviation of NN intervals;
- pNN50: proportion of successive differences exceeding 50 ms;
- frequency-domain HRV: spectral structure of the interval series.

These require substantially more temporal information than a simple HR estimate. Radar HRV literature commonly uses 60 s, 300 s, or multi-minute recordings; a 20 s HR window should therefore not be inherited as the formal HRV window without dedicated validation.

## 4. Why HRV cannot be 'calculated from HR' after the fact

A crucial distinction:

`average HR` does not contain HRV.

For example, two 60-second recordings can both have average HR = 60 bpm:

- person A: IBIs = 1.00, 1.00, 1.00, 1.00 ...
- person B: IBIs = 0.80, 1.20, 0.85, 1.15 ...

The average HR can be similar while HRV is completely different.

Therefore:

- HR can be derived from a validated IBI sequence;
- HRV cannot be reconstructed from a single average HR estimate.

This is the reason the cardiac branch should prioritize preserving beat timing if HRV is a project goal.

## 5. Recommended FocusWave architecture — reuse-first, no new algorithm family

This is a project decision constrained by the existing producer and literature evidence, not authorization to build a new pipeline immediately.

### Shared upstream

Reuse the most complete existing producer for:

`range-domain input -> target/bin/channel handling -> phase extraction -> detrending/filtering/decomposition`.

Do not create separate HR and HRV target-selection systems unless existing evidence proves the shared target path is inadequate.

### BR branch

Continue a respiration-specific branch using the low-frequency respiratory component.

Required output:

- BR / respiratory waveform;
- quality evidence;
- optionally respiration information usable for cardiac harmonic diagnostics.

### Cardiac branch

The principal scientific target should become a validated cardiac beat representation.

Use existing historical producer components first: bandpass/decomposition, candidate detection, harmonic handling, temporal continuity, segment consensus, etc. Restore existing stages only when controlled evidence supports them.

Output both:

1. beat-derived HR / mean HR;
2. IBI series for HRV.

Retain the existing spectral HR estimate as a QC/fallback/consistency output while beat-level validity remains under study.

### HRV branch

Do not use the 20 s HR diagnostic contract as the default HRV contract.

The next HRV gate must be:

1. radar beat timestamps vs ECG R-peaks;
2. paired IBI error / agreement;
3. only after beat-level validation, calculate HRV on explicitly chosen longer windows;
4. start from literature-supported 60 s / 300 s or other predeclared windows depending on the metric, rather than selecting the window by whichever produces the best error.

## 6. What should be done now versus later

### Do now

- finish restoration/controlled validation of the existing cardiac producer stages;
- establish whether the existing producer can recover stable beat timing, not only average HR;
- keep BR as its own low-frequency branch;
- calculate beat-derived HR whenever beat timing becomes available and compare it with existing spectral HR;
- preserve the existing HR spectral estimator as independent QC while beat-level validation is incomplete.

### Do not do now

- do not create a separate new HRV signal-extraction pipeline from scratch;
- do not calculate HRV from 20 s average HR estimates;
- do not infer HRV validity from a low HR MAE;
- do not tune HRV windows against ECG to obtain the best result;
- do not promote VMD, harmonic guards, static suppression, or any new target rule without controlled evidence.

## 7. Current FocusWave scientific status after this clarification

- HR: remains HOLD. Existing selector/fusion restoration has improved supporting HR error substantially, but formal validity is not yet established.
- BR: remains HOLD/supporting. It is a separate low-frequency physiological output that shares upstream target/phase processing.
- HRV: remains BLOCKED. The blocker is not merely '20 s is short'; the more fundamental blocker is missing validated radar beat timestamp <-> ECG R-peak and paired IBI agreement.
- 20 s: acceptable as a bounded HR diagnostic/estimator window where separately validated; it is not automatically an HRV window.
- HRV window: must be separately frozen only after beat-level validation, with literature-supported longer intervals such as 60 s / 300 s evaluated by predeclared metric-specific contracts.

## 8. References used for this decision

1. F. Wang, X. Zeng, C. Wu, B. Wang, K. J. R. Liu. "mmHRV: Contactless Heart Rate Variability Monitoring Using Millimeter-Wave Radio." IEEE Internet of Things Journal, 8(22), 16623-16636, 2021. DOI: 10.1109/JIOT.2021.3075167.
2. H. Wang, J. Chen, D. Zhang, Z. Lu, C. Wu, Y. Hu, Q. Sun, Y. Chen. "Contactless Radar Heart Rate Variability Monitoring Via Deep Spatio-Temporal Modeling." ICASSP 2024, 111-115.
3. F. Wang, F. Zhang, C. Wu, B. Wang, K. J. R. Liu. "ViMo: Multiperson Vital Sign Monitoring Using Commodity Millimeter-Wave Radio." IEEE Internet of Things Journal, 8(3), 1294-1307. DOI: 10.1109/JIOT.2020.3004046.
4. L. Liu et al. "mmRH: Noncontact Vital Sign Detection With an FMCW mm-Wave Radar." IEEE Sensors Journal, 23(8), 8856-8866, 2023. DOI: 10.1109/JSEN.2023.3250500.
5. Current FocusWave canonical mmWave producer/pipeline audits and selector-path controlled evidence under `docs/research/` and `docs/results/2026-08-30_MMWAVE_SELECTOR_PATH_RECONCILIATION/`.

Evidence boundary: literature establishes the architecture and the need for beat-level IBI validation; it does not prove that the current FocusWave radar data already meet HRV validity requirements.