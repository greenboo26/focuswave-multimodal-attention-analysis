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

### M5 — Wei et al., 2022, Sensors review

- Title: *MmWave Radar and Vision Fusion for Object Detection in Autonomous Driving: A Review*
- DOI: `10.3390/s22072542`
- Although the application is object detection, it gives a clear fusion taxonomy: data-level, feature-level and decision-level fusion, with trade-offs.
- Relevance to FocusWave: because current producers already output modality-specific engineered features, feature-level/late fusion is much more natural than raw-data fusion. The application domain is different, so this is methodological—not cognitive-state—evidence.

### M6 — Tac-Mamba, 2026

- Title: *Tac-Mamba: A Pose-Guided Cross-Modal State Space Model with Trust-Aware Gating for mmWave Radar Human Activity Recognition*
- Journal: Electronics 15(7):1535
- DOI: `10.3390/electronics15071535`
- Relevance: modern example of trust-aware/gated multimodal fusion designed to reduce negative transfer when one modality degrades. This supports the engineering plausibility of FocusWave's proposed quality-aware gating, but it is HAR rather than cognitive-state evidence.

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
