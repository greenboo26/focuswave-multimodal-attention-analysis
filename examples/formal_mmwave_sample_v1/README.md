# Formal RS6240 mmWave structure sample v1

This directory contains a small de-identified excerpt from one formal experiment block. It is provided only so another analysis agent can inspect the actual saved RS6240 structure without access to the local J: drive.

The source subject identifier, absolute Unix timestamps, local paths, behavior files, RGB/NIR files and full-session data are intentionally excluded. This sample is not a quality result and must not be used as a participant-level scientific result.

## Contents

- `mmwave_part_001_60s.npz` to `mmwave_part_003_60s.npz`: three consecutive approximately 60-second chunks.
- `timestamps_relative.csv`: frame index and the two timestamp columns converted to relative milliseconds. The original CSV had no header, so their physical semantics are not asserted here.
- `metadata_sanitized.json`: saved metadata that is safe to expose, including 2T4R, frame rate and array structure.
- `raw_frame_sample.bin`: a small binary excerpt containing the file header and two frame records. It is included for format inspection, not for analysis.
- `sample_manifest.json`: purpose and de-identification boundaries.

## Confirmed NPZ structure

Each NPZ contains eight independent arrays:

```text
tx0_rx0 ... tx0_rx3
tx1_rx0 ... tx1_rx3
```

Each array is a complex-valued matrix with shape `(frames, 256)`. The first dimension is the frame/time dimension. The second dimension is the 256-sample fast-time dimension present in the saved file. A physical range axis is not included.

Minimal reader:

```python
import numpy as np

z = np.load("mmwave_part_001_60s.npz", allow_pickle=False)
for name in z.files:
    x = z[name]
    print(name, x.dtype, x.shape, np.iscomplexobj(x))
```

The sample preserves the complex I/Q representation. Phase can be derived with `np.angle(x)`; there is no precomputed `phase` field, no `range_m` field and no angle/beamforming field.

## Interpretation boundary

The sample supports inspection and development of readers, range-FFT/range-bin reconstruction and channel-level phase processing. It does not by itself establish target lock, chest-wall origin, heart rate accuracy, beat accuracy or HRV validity.
