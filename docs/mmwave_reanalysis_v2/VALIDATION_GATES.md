# Validation gates

| Gate | Pass condition | Failure action |
|---|---|---|
| G0 provenance | source manifest, commit/hash, script, config and output path all recorded | `BLOCKED` |
| G1 reference quality | ECG/RSP own QC passes; valid reference coverage >=80% for scored interval | exclude interval with reason |
| G2 synchronization | timestamp origin and lag rule frozen; no per-window lag search | `BLOCKED` for beat claim |
| G3 BR | raw-RSP-backed participant/window coverage >=80%; MAE <=2 rpm; median AE <=1.5; RMSE <=3; correlations >=.80; abs bias <=1; LoA within ±5; P90 AE <=5 | BR remains `BLOCKED` |
| G4 HR | participant/window coverage >=80%; MAE <=5 bpm; median AE <=3; RMSE <=8; correlations >=.85; abs bias <=2; LoA within ±10; P90 AE <=10; 2x/half locks each <=1% | HR remains supporting only |
| G5 HRV | future beat gate: coverage >=80%; precision/recall/F1 >=.90; timing and IBI MAE <=50 ms; abs IBI bias <=10 ms; LoA within ±100 ms | HRV remains `BLOCKED`; frozen gate does not authorize scoring |

All values are controlled by `benchmark_decision_v1.json`; prose is a pointer. Respiratory-harmonic lock must be <=2% only where valid RSP makes it assessable.
| G6 formal preflight | target-lock, motion, timestamp, range stability and usable-window coverage manifest complete | no formal HR/BR application |
| G7 formal application | frozen benchmark method/config applied without silent interpolation; per-window status emitted | stop and preserve partial output |
| G8 science inference | physiology features retain validated names; signal-only features separately labelled; grouped/frozen folds reused | no upgrade to scientific claim |
| G9 product model | deployment features and teacher labels separated from physiological validation | product result cannot imply physiology validity |
