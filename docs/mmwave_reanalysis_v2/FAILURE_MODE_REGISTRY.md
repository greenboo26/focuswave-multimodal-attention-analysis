# Failure-mode registry

| ID | Failure mode | Evidence | Consequence | Required control | State |
|---|---|---|---|---|---|
| F-001 | 2nd/3rd respiratory harmonic enters HR band | v9 notes; 2025/2024 external literature | strong false HR candidate | explicit harmonic modelling and lock-rate reporting | OPEN |
| F-002 | strongest range bin is clutter/multipath, not chest | target-lock docs and early delivery package | false physiological signal | target-lock + multi-bin/spatial consistency | OPEN |
| F-003 | VMD mode selection instability | historical Q&A and v2/v3 code comments | irreproducible HR/IBI | freeze mode-selection rule; benchmark all candidates | OPEN |
| F-004 | beat timing delay differs from HR accuracy | official VitalSense reproduction | plausible HR but poor beat recall/HRV | session sync and beat-level coverage gate | OPEN |
| F-005 | ECG T-wave double detection | 2026-08-16 cleaning record | doubled ECG HR and invalid benchmark | ECG quality audit before radar comparison | CONTROLLED |
| F-006 | RSP natural variability mistaken for artifact | 2026-08-16 cleaning record | underestimates BR quality | do not apply 17% jump rule to static RSP | CONTROLLED |
| F-007 | movement/edge exposure changes radar quality | RGB-mmWave gate history | spurious BR/HR/HRV | motion gate and per-window reject status | OPEN |
| F-008 | sparse/single-bin signal lacks spatial redundancy | early subject-001 notes | harmonic lock survives bin voting | temporal continuity only as diagnostic, never silent correction | OPEN |
| F-009 | no RSP in external dataset | VitalSense example schema | BR claim impossible | mark BR unvalidated; use only HR/ECG | CONTROLLED |
| F-010 | historical results lack exact output/params | repository/archive audit | cannot reproduce or upgrade evidence | `MISSING_EVIDENCE`; no guessed values | OPEN |
