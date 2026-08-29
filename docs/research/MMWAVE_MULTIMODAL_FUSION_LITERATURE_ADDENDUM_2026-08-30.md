# mmWave multimodal fusion literature addendum — 2026-08-30

Status: `LITERATURE_EVIDENCE / NO EXECUTION AUTHORIZATION`

Purpose: add literature evidence specifically for mmWave participation in multimodal cognitive-state / attention-adjacent fusion. This is a linked addendum to `MMWAVE_LITERATURE_EVIDENCE_AND_DECISION_LEDGER_2026-08-29.md`, `MULTIMODAL_COMPLEMENTARITY_ANALYSIS_DESIGN_2026-08-30.md`, and `MULTIMODAL_AI_INTEGRATION_DESIGN_2026-08-30.md`; it does not replace those documents.

## LITERATURE_EVIDENCE

### M1 — CogPhys, NeurIPS 2025 Datasets & Benchmarks

- Title: *CogPhys: Assessing Cognitive Load via Multimodal Remote and Contact-based Physiological Sensing*
- Venue: NeurIPS 2025 Datasets & Benchmarks Track
- Sensors: RGB stereo, NIR, two thermal cameras, mm-wave/RF radar, plus contact reference sensors.
- Scientific task: cognitive-load estimation during reading, memorization, arithmetic and related tasks.
- Pipeline: remote modalities estimate PPG/respiration/blink waveforms and derived HR/HRV/RR/blink metrics, then estimate cognitive load.
- Reported benchmark: remote PPG + remote respiratory signals + blink markers reached 86.49% cognitive-load classification accuracy versus 87.5% for contact-based sensing.
- Relevance: very close precedent for FocusWave's `mmWave + NIR + RGB -> cognitive state` framing and for treating radar as one complementary physiological source rather than the sole estimator.
- Sources: https://papers.nips.cc/paper_files/paper/2025/hash/014e80b61aca7a85630e6da5d63427c6-Abstract-Datasets_and_Benchmarks_Track.html ; https://papers.neurips.cc/paper_files/paper/2025/file/014e80b61aca7a85630e6da5d63427c6-Paper-Datasets_and_Benchmarks_Track.pdf
- Sensor-layout evidence: Section 3.2 states that RGB/NIR are mounted in front of the participant, while the radar is placed behind the seat within a plastic enclosure. Direct source: https://openreview.net/pdf/fdf18cf3037df03a17e49c167acbff550548d7c3.pdf . This is a successful alternative geometry, not evidence that front-facing and rear-seat geometries are equivalent.

### M2 — Wang et al., 2026, WORK

- Title: *Workers/crews’ mental workload dynamics in closed cabins: A task-difficulty-adaptive random forest model for instrument monitoring tasks using multimodal biosignals*
- DOI: `10.1177/10519815261440247`
- Design: 30 participants; four mental-workload levels; millimeter-wave radar + camera used for fully non-contact multimodal physiological monitoring including cardiopulmonary and eye-movement information.
- Model: Random Forest; reported 83.33% accuracy for four workload levels.
- Relevance: direct empirical precedent that radar-derived cardiopulmonary information and camera-derived ocular information can be combined for cognitive-state classification.
- Source: https://doi.org/10.1177/10519815261440247

### M3 — Hao et al., 2023, Sensors

- Title: *Wireless Sensing Technology Combined with Facial Expression to Realize Multimodal Emotion Recognition*
- Journal: Sensors 23(1):338
- DOI: `10.3390/s23010338`
- Inputs: mmWave heartbeat/respiration + camera facial-expression images.
- Architecture: separate CNN feature extraction for modalities, parallel feature fusion, then GRU temporal classification.
- Reported accuracy: 84.5% person-dependent and 74.25% person-independent.
- Relevance: not an attention paper, but a close architectural precedent for `mmWave physiology + visual behavior -> higher-order psychological state` and a warning that subject-independent performance is materially lower than subject-dependent performance.
- Source: https://www.mdpi.com/1424-8220/23/1/338

### M4 — Wang et al., IEEE Communications Surveys & Tutorials

- Title: *Multi-Modal Fusion Sensing: A Comprehensive Review of Millimeter-Wave Radar and Its Integration With Other Modalities*
- DOI: `10.1109/COMST.2024.3398004`
- Journal: IEEE Communications Surveys & Tutorials 27(1):322–352.
- Scope: comprehensive review of mmWave multimodal sensing, data representations, fusion algorithms and applications.
- Relevance: authoritative survey support for treating mmWave as a complementary modality in heterogeneous sensing rather than requiring radar alone to explain the target state.
- Source: https://doi.org/10.1109/COMST.2024.3398004

### M5 — Wei et al., 2022, Sensors review

- Title: *MmWave Radar and Vision Fusion for Object Detection in Autonomous Driving: A Review*
- DOI: `10.3390/s22072542`
- Although the application is object detection, it gives a clear fusion taxonomy: data-level, feature-level and decision-level fusion, with trade-offs.
- Relevance to FocusWave: because current producers already output modality-specific engineered features, feature-level/late fusion is much more natural than raw-data fusion. The application domain is different, so this is methodological—not cognitive-state—evidence.
- Source: https://www.mdpi.com/1424-8220/22/7/2542

### M6 — Tac-Mamba, 2026

- Title: *Tac-Mamba: A Pose-Guided Cross-Modal State Space Model with Trust-Aware Gating for mmWave Radar Human Activity Recognition*
- Journal: Electronics 15(7):1535
- DOI: `10.3390/electronics15071535`
- Relevance: modern example of trust-aware/gated multimodal fusion designed to reduce negative transfer when one modality degrades. This supports the engineering plausibility of FocusWave's proposed quality-aware gating, but it is HAR rather than cognitive-state evidence.
- Source: https://www.mdpi.com/2079-9292/15/7/1535

## METHOD COMPARISON — what each paper actually does and what it means for FocusWave

| Source | Target task | Sensor roles | Fusion point / model | Reported evaluation/result | What FocusWave may borrow | What must NOT be inferred |
|---|---|---|---|---|---|---|
| CogPhys 2025 | cognitive load | RGB/NIR/thermal/mmWave provide remote physiology/ocular information; contact sensors serve as reference/comparison channels | remote signals are converted to physiological markers such as PPG/respiration/blink and derived HR/HRV/RR before higher-level cognitive-load prediction | remote PPG + remote respiration + blink markers: 86.49%; contact-based sensing: 87.5% | `sensor -> interpretable physiological/ocular features -> cognitive-state model`; mmWave as a complementary source rather than sole predictor | does not prove FocusWave HR/BR are valid; their radar placement/processing and dataset are not interchangeable with ours |
| Wang et al. 2026 WORK | four-level mental workload | mmWave contributes cardiopulmonary information; camera contributes ocular information | engineered multimodal biosignals -> Random Forest | 30 participants; 83.33% four-level accuracy | direct precedent for `radar cardiopulmonary + camera ocular -> cognitive state`; Random Forest is a reasonable nonlinear robustness baseline | does not justify copying their accuracy or assuming our physiology features have equal quality |
| Hao et al. 2023 Sensors | emotion recognition | mmWave heartbeat/respiration + camera facial expression | modality-specific CNNs -> feature fusion -> GRU temporal classifier | 84.5% person-dependent; 74.25% person-independent | precedent for modality-specific encoders followed by feature/temporal fusion; reinforces participant-independent evaluation | emotion is not attention; the neural architecture is not automatically superior for our sample size |
| Wang et al. COMST review | broad mmWave multimodal sensing | mmWave combined with heterogeneous sensing modalities | reviews data-level, feature-level and decision-level families and multimodal algorithms | review, not one benchmark | supports selecting fusion level explicitly and treating mmWave as complementary heterogeneous sensing | does not prescribe one universal fusion architecture |
| Wei et al. 2022 review | radar-camera object detection | radar + vision | taxonomy of data-level / feature-level / decision-level fusion | review | clear methodological taxonomy and diagrams for explaining where fusion occurs | application is object detection, so it is method evidence only, not cognitive-state evidence |
| Tac-Mamba 2026 | human activity recognition | mmWave + pose/visual-like complementary information | cross-modal model with trust-aware gating | task-specific HAR evaluation | supports the engineering idea that modality trust can be dynamically down-weighted when one stream degrades | gate weights are model behavior, not causal physiological importance; HAR is not attention |

### Plain-language translation of the fusion levels

- `data-level / early fusion`: combine raw or very low-level streams before each modality has been independently summarized. This is the heaviest synchronization/modeling option and is **not** the current FocusWave default.
- `feature-level fusion`: each modality first produces its own interpretable or learned features, then the feature blocks are concatenated or jointly modeled. This matches the current formal producer architecture most naturally.
- `decision-level / late fusion`: each modality makes a separate prediction first, then those predictions are combined. Quality-aware gated fusion is a learned form of late/intermediate fusion when the model changes how much it trusts each modality per sample/window.
- `gating`: a learned reliability weighting mechanism. In plain language: if NIR is occluded in one window, the fusion model can reduce NIR's contribution and rely more on other available modalities. A gate weight is **not** a causal statement such as “mmWave explains 40% of attention.”
- `person-independent`: the tested participant is absent from training. FocusWave's LOSO rule is a participant-independent evaluation design.

### Direct method decision for FocusWave

The literature comparison does **not** justify replacing the frozen analysis plan. It strengthens the current order:

1. formal modality-specific features/QC first;
2. same matched cohort and participant-disjoint folds;
3. interpretable feature-level fusion first (`C/M/N/R` subset ladder);
4. quantify incremental/conditional contribution on identical held-out participants;
5. Random Forest may be used as a prespecified nonlinear robustness model;
6. small MLP may test learned feature interactions;
7. quality-aware gated fusion is a secondary AI model only after simple fusion is stable;
8. raw-data end-to-end fusion / large Transformer is not justified under the current evidence/sample constraints.

## SENSOR PLACEMENT BOUNDARY — CogPhys rear-seat radar is a precedent, not an equivalence claim

CogPhys reports the radar positioned behind the seat inside a plastic enclosure while the visual sensors are placed in front. This is evidence that mmWave cardiopulmonary sensing is not physically restricted to a front-of-chest layout. It does **not** establish that rear-seat, front-chest and side-on geometries are equivalent: radar phase is sensitive to the radial component of body-surface displacement, and orientation/material path can change the observed signal.

Project decision: retain the actual FocusWave acquisition geometry as the only geometry for interpreting FocusWave data. Do not retroactively infer that a successful rear-seat setup validates our front placement or vice versa. The CogPhys layout is retained as a methodological precedent only.

CogPhys sources: https://papers.nips.cc/paper_files/paper/2025/file/014e80b61aca7a85630e6da5d63427c6-Paper-Datasets_and_Benchmarks_Track.pdf ; https://openreview.net/pdf/fdf18cf3037df03a17e49c167acbff550548d7c3.pdf

## PROJECT INTERPRETATION

The strongest directly relevant precedent is CogPhys: it already uses concurrent RGB, NIR and mm-wave/RF sensing for cognitive-load estimation, with radar-derived respiratory/cardiovascular information and visually derived blink information feeding a higher-order cognitive-state model. The WORK 2026 paper independently supports the same general physiological-plus-ocular multimodal concept.

Therefore FocusWave's planned analysis is not an exotic sensor combination. The scientifically conservative route remains:

1. modality-specific formal features/QC;
2. same-cohort participant-disjoint evaluation;
3. interpretable feature-level fusion first;
4. quantify each modality's incremental contribution;
5. only then test a quality-aware gated model;
6. do not infer causal physiology from learned gate weights.

Sensor-layout boundary: literature establishes that successful mmWave vital-sign sensing can be implemented with different geometries, including front-facing and behind-seat placement. This does **not** justify treating geometries as interchangeable. FocusWave must interpret its own formal acquisition according to its actual front-side geometry; no acquisition-layout change or retrospective geometry correction is implied.

## DECISION

No change to the frozen multimodal design is required from this literature review. The new evidence strengthens the rationale for the current `C/M/N/R` feature-level complementarity ladder and the optional quality-aware gated fusion stage. It does not authorize raw-data end-to-end fusion, large Transformers, or promotion of blocked mmWave HRV.
