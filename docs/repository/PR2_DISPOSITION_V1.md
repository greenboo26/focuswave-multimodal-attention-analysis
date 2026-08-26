# PR #2 disposition V1

Recommendation: `KEEP_OPEN_AND_UPDATE`, not merge or close in this task.

PR #2 head is `chatgpt/multimodal-results-nir-diagnostic-20260826@0e756b275fd9cbbc7d7564531d3200425bf3be23`; observed merge ref is `59955a997a75c9581792b22e26f5a78afe139259`. Its useful content is the NIR feature contract, diagnostic provenance and recovery-aware planning. All NIR numeric results in the snapshot are pre-recovery current results; the 68-session/44-participant/1,360-probe NIR v1 remains the current pre-recovery boundary.

The prior RGB formal-analysis priority is stale: RGB is now pipeline engineering pending and formal statistics are not authorized. mmWave HRV must not return as the near-term mainline. Before a future merge to `main`, PR #2 must update the NVIDIA ref to `36a2d596c55b93071a8b5c80459a56c876c06351`, distinguish 32-frame smoke recovery from fullclass/Probe/QC completion, state sub-099's timeline blocker, and provide an approved aggregate result/provenance update.
