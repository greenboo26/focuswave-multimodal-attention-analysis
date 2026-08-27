# Open gaps

| ID | Gap | Impact | Required resolution | State |
|---|---|---|---|---|
| O-001 | exact AgeBalanced file/subject/session manifest and 220-session reconciliation | external result provenance ambiguous | reconciled in `agebalanced_provenance_v1.json`; 220 = two Rest sessions ×110; source hashes frozen | RESOLVED |
| O-002 | VS_DATASET healthy official data access and license/file inventory | cannot repeat full benchmark from clean checkout | obtain approved files and record access provenance | BLOCKED |
| O-003 | historical A/B result tables and exact per-method parameters | cannot reproduce seven trials | recover reports/output manifests; otherwise retain MISSING_EVIDENCE | OPEN |
| O-004 | formal J:\\Data canonical session inventory and target-lock mapping | cohort scope not yet frozen | run read-only target/timestamp/range audit | OPEN |
| O-005 | exact v1.1-v1.7 naming and artifact crosswalk | version history is partly narrative | build commit-to-script-to-output crosswalk | OPEN |
| O-006 | official ECG/RSP 8/16 workflow applicability per device | reference quality may differ by dataset | `ecg_reference_v1`/`rsp_reference_v1` frozen; RS6240 inventory found ECG 11/RSP 10, two ID mismatches and missing derived linkage | PARTIAL |
| O-007 | compatible raw/angle data for beamforming | multi-bin methods may not be implementable | inspect RS6240 schema and antenna calibration | OPEN |
| O-008 | mature external implementations lack fixed commits/licence audit | reuse cannot yet be merged | fixed in `reuse_gate_v1.json`; candidates without license/code are explicitly blocked or `paper_reimplementation` | RESOLVED_AUDIT / PARTIAL_EXECUTABLE |
| O-009 | predeclared numeric HR/BR/beat thresholds | gates cannot be scored without value choices | frozen in Decision V1 with separate justification | RESOLVED |
| O-010 | no canonical V2 machine-readable per-window schema | downstream integration risk | JSON Schema and tests implemented | RESOLVED |
| O-011 | AgeBalanced record-specific license metadata | redistribution/adoption boundary incomplete | recover trustworthy Zenodo record metadata; do not infer default license | MISSING_EVIDENCE |
| O-012 | RS6240 identity/linkage anomalies | two ACQ names disagree with folder/meta IDs; raw-to-derived windows unproven | adjudicate `sub-97795_/97995.acq` and `sub-97994_/97794.acq`, then hash radar BIN/derived linkage | BLOCKED |
