# Formal mmWave pipeline flowchart

Status: source-controlled audit visual; no new analysis is implied.

```mermaid
flowchart LR
    A[RS6240 formal firmware image<br/>fft_mode=2; 256; 37 mm/bin] --> B[1D range-domain DataCube<br/>2 TX x 4 RX x 256 complex16]
    B --> C[HIF 0xC2 ReportDataCube1D]
    C --> D[SDK DatacubeConversion]
    D --> E[NPZ chunks<br/>frame x range-bin x 8 complex]
    E --> F[Behavior/timestamp segment mapping]
    F --> G[Mean |z|^2 range profile<br/>no proven downstream DC/clutter correction]
    G --> H{Distance gate}
    H -->|formal semantics should be 0.037 m/bin| I[Candidate bins]
    H -->|legacy default 0.08 m/bin remains in producer| J[Potentially harmful gate mismatch]
    I --> K[Per-channel phase variance<br/>HR/BR spectral scores]
    K --> L[Independent BR and HR bin/channel choice]
    L --> M[Phase angle -> unwrap -> displacement]
    M --> N[BR branch: detrend / diff+smooth / 0.10-0.50 Hz]
    N --> O[BR time + periodogram consensus]
    M --> P[HR 0.80-2.00 Hz]
    P --> Q[VMD K=3, 40 s/20 s overlap]
    Q --> R[Peak candidates + periodogram]
    R --> S{External RSP passed?}
    S -->|standard formal runner: no| T[Reference/time harmonic folding only]
    S -->|optional calibration path| U[Scalar RSP 2x/3x candidate rejection]
    T --> V[HR time/frequency fusion + smoothing]
    U --> V
    V --> W[10 s HR signal-existence gate]
    M --> X[HRV-shaped path: peaks -> IBI -> SDNN/RMSSD]
    X --> Y[No ECG beat-level alignment]
    O --> Z[BR output + consistency label]
    W --> AA[HR candidate output]
    Y --> AB[HRV validation blocked]
    Z --> AC[Existing formal QC/coverage/tier crosswalk]
    AA --> AC
    AC --> AD[33/37/2 = current-pipeline eligibility strata]
    AD --> AE[Not participant compliance, acquisition quality, or physiology validity]
```

Legend: solid links are observed code/data flow; the RSP branch is optional and is not active in the standard formal batch; the red-flag conceptual branch records the known 0.08 m/bin dependency rather than changing it.
