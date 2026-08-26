# Cross-repository provenance V1

NIR/RGB producer source: `kyandi233-dev/Attention-Analysis`.

| role | approved ref evidence | boundary |
|---|---|---|
| NVIDIA production | `nvidia-cuda` remote ref `01af297676399dcf316c1eca8201b4d3aa892023` | timestamp/NIR production; requires Gate 0 |
| AMD production | `amd-DirectML` remote ref `e519373f48c5665226d23334969d419181ccfdda` | DirectML local production; requires Gate 0 |
| RGB engineering | rgb-nvidia/rgb-amd family | engineering first; formal stats not authorized |
| central analysis | this candidate branch | identity, folds, matched inference, report surface |

Read-only blob comparison found 6,018 common paths, 5,982 identical blobs and 36 differing blobs between the two fetched NIR branches; branch name alone is not scientific equivalence. The differing implementation/config/runtime/test files require backend provenance and representative parity, not silent merging.

The current NIR diagnostic PR #2 is `chatgpt/multimodal-results-nir-diagnostic-20260826@0e756b275fd9cbbc7d7564531d3200425bf3be23`, with merge ref observed as `59955a997a75c9581792b22e26f5a78afe139259`. It is pre-timestamp-recovery diagnostic evidence, not a final multimodal result.
