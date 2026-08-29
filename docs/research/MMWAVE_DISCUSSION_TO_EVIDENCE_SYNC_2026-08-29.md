# mmWave discussion → evidence sync — 2026-08-29

Status: `CURRENT DISCUSSION RECORD`

This file preserves the user-facing explanation of **where the remaining pipeline answers can be found**. It is intentionally written in plain language so future agents do not force the user to reconstruct the same discussion.

## What is already known

The project is no longer asking “did the radar do Range FFT?” That has been closed. The formal path is already bound to a 256-point, 37 mm/bin, 2T×4R complex 1D Range-FFT DataCube. The remaining questions are narrower implementation and validation questions.

## Where to find the answer for each remaining question

### 1. Window / FFT / zero padding / scaling / clutter

Look in the RS6240 official SDK, formal configuration, lower-layer DSP implementation, and official manual/API documentation.

This is where the project can determine:

- whether a pre-FFT window exists;
- which window is used;
- FFT length;
- zero padding;
- scaling/normalization;
- DC/static clutter handling.

The critical distinction is that official SDK support is not automatically proof of execution in the exact formal firmware.

### 2. IQ and channel calibration

Look in calibration routines, initialization code, calibration tables, EEPROM/flash loading logic, and official calibration documentation.

Three evidence levels must be separated:

1. the SDK supports calibration;
2. the formal firmware calls it;
3. the formal experiment device actually loaded/used valid calibration.

Only the third directly establishes deployment behavior.

### 3. Tx/Rx/TDM timing and phase compensation

Look in chirp/frame configuration, Tx switching sequence, chirp interval, antenna/channel mapping, official timing diagrams, and any TDM phase-compensation code.

The project must separately establish:

- the timing/order itself;
- whether phase compensation is performed.

They are not the same fact.

### 4. Which firmware actually ran during formal acquisition

This cannot be proven by source code alone.

Look for:

- flash/programming logs;
- serial/boot output;
- device information/version records;
- acquisition metadata;
- GUI or capture logs with build/version identifiers.

This is the deployment binding between the audited firmware image and the actual experiment device.

### 5. Whether target/bin/channel jumps across windows

This answer is in project outputs, not the device manual.

Use persisted selected-bin/channel data, target-lock audit tables, producer summaries, or equivalent existing outputs.

The audit should examine:

- HR selected bin/channel per window;
- BR selected bin/channel per window;
- changes relative to the previous window;
- whether phase instability appears around switching.

If those histories were not persisted, document the minimal instrumentation needed before any rerun.

### 6. Whether phase instability is real participant movement

This requires combining:

- radar selected bin/channel timeline;
- radar phase timeline;
- independent motion evidence already available, such as RGB motion, keypress timing, or a radar motion/Doppler proxy where appropriate.

A phase jump without independent motion evidence, especially when accompanied by target/bin/channel switching, cannot be called participant movement automatically.

### 7. Whether formal HR really suppresses 2×BR / 3×BR harmonics

Trace the exact formal invocation:

`formal runner → process_vital_signs_v3_1_1.py → harmonic rejection logic`.

The answer comes from function definitions, call sites, branch conditions, and actual arguments such as whether `acq_path`/RSP is supplied.

Code containing a harmonic function does not mean the formal runner actually executes it.

### 8. Whether HRV is valid

This cannot be answered by manuals or by a window-level HR output.

The required evidence is:

- radar beat timestamps;
- radar IBI sequence;
- ECG R-peak timestamps;
- synchronization mapping;
- beat-to-beat matching.

If the chain breaks at any earlier layer, HRV stays `BLOCKED`.

## Current execution decision

The next work should proceed in this order:

1. close device/firmware engineering unknowns;
2. audit target/bin/channel continuity using existing outputs;
3. prove whether formal respiratory-harmonic suppression is active;
4. identify the earliest missing HRV beat/ECG layer;
5. only after those are closed reconsider #16.

This discussion is now durable in GitHub and must not need to be reconstructed from chat.
