# Cross-repository provenance V1

NIR/RGB producer source: `kyandi233-dev/Attention-Analysis`.

| role | approved ref evidence | boundary |
|---|---|---|
| NVIDIA production | `nvidia-cuda@36a2d596c55b93071a8b5c80459a56c876c06351` | canonical sequential AVI mapping; 69/72 formal fullclass complete; Gate 0/recovery QC required |
| AMD production | `amd-DirectML@d8e721079461ef7f71fafcd3edf819858fabbb16` | DirectML local production; requires Gate 0 |
| RGB engineering | `rgb-nvidia@9b10ca16162ae5f1af5920848e351ec01575bfbc`, `rgb-amd@713ef1a780f9a67295c0776c55c20a3d81b4a025` | engineering first; formal stats not authorized |
| central analysis | this candidate branch | identity, folds, matched inference, report surface |

Read-only blob comparison found 6,018 common paths, 5,982 identical blobs and 36 differing blobs between the two fetched NIR branches; branch name alone is not scientific equivalence. The differing implementation/config/runtime/test files require backend provenance and representative parity, not silent merging.

The latest NVIDIA mapping result proves the old sub-100/sub-178 issue was not a true AVI frame-gap blocker. Both sessions are now `RECOVERABLE_PENDING_FULL_RECOVERY_QC_PROBE_ALIGNMENT`; only 32-frame smoke validation exists, not complete fullclass or Probe alignment. `sub-099` remains a `master_timeline` blocker. The current NIR v1 remains the pre-recovery 68-session/44-participant/1,360-probe result and must be rerun under the frozen rule if the recovered cohort changes.

The current NIR diagnostic PR #2 is `chatgpt/multimodal-results-nir-diagnostic-20260826@0e756b275fd9cbbc7d7564531d3200425bf3be23`, with merge ref observed as `59955a997a75c9581792b22e26f5a78afe139259`. It remains pre-recovery diagnostic evidence, not a final multimodal result.
