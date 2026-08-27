# Validation gates

| Gate | Pass condition | Failure action |
|---|---|---|
| G0 provenance | source manifest, commit/hash, script, config and output path all recorded | `BLOCKED` |
| G1 reference quality | ECG/RSP own QC passes; valid reference coverage >=80% for scored interval | exclude interval with reason |
| G2 synchronization | timestamp origin and lag rule frozen; no per-window lag search | `BLOCKED` for beat claim |
| G3 BR | RSP-backed coverage and error metrics meet benchmark threshold; exact thresholds frozen before scoring | BR remains `BLOCKED` |
| G4 HR | held-out subject benchmark reports coverage, MAE/median AE/RMSE, BA and lock rates; no quality-stratum collapse hidden | HR remains supporting only |
| G5 HRV | matched IBI coverage threshold and predeclared IBI error threshold met on held-out ECG; session/window completeness recorded | HRV remains `BLOCKED` |
| G6 formal preflight | target-lock, motion, timestamp, range stability and usable-window coverage manifest complete | no formal HR/BR application |
| G7 formal application | frozen benchmark method/config applied without silent interpolation; per-window status emitted | stop and preserve partial output |
| G8 science inference | physiology features retain validated names; signal-only features separately labelled; grouped/frozen folds reused | no upgrade to scientific claim |
| G9 product model | deployment features and teacher labels separated from physiological validation | product result cannot imply physiology validity |
