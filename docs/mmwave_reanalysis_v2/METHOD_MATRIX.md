# Method matrix and Reuse Gate

| Method | Problem addressed | Local prior art | External provenance | Input / parameter burden | Fit decision |
|---|---|---|---|---|---|
| Dual-bin bandpass | transparent BR/HR baseline | v1/v2/v3/v5; 0.1–0.5 Hz BR, 0.8–2.5 Hz HR | Alizadeh 2019; Paterniani 2023 | phase waveform, target bin | retain as benchmark baseline |
| VMD heart-only | mode mixing / separation | `process_vital_signs_v3.py`, v5; alpha=1000, K=4 historical; v3.1.1 K=3 | Dragomiretskiy & Zosso 2014; Wang et al. 2021 mmHRV | sensitive to K/alpha and mode selection | benchmark candidate, not default |
| SSA + VMD / EE/PCC-VMD | noise and respiratory harmonics entering HR band | SSA A/B exists but was not adopted | Lei et al., DSP 2025, DOI `10.1016/j.dsp.2024.104911`; SSA-VMD UWB PMC9861067 | window/embedding rank, VMD K/alpha; device transfer risk | high-priority reproduction candidate |
| DR-MUSIC | adaptive cancellation plus high-resolution spectral estimation | no local implementation | Chen et al., Sci Rep 2024, DOI `10.1038/s41598-024-77683-1` | RLS order/forgetting, differential stage, MUSIC model order | reproduce only if inputs and parameters can be frozen |
| Harmonic MUSIC / joint harmonic estimation | select fundamental while modelling harmonics | no local implementation | Harmonic MUSIC arXiv `2408.01951`; related sparse reconstruction source | model order, harmonic set, regularization | candidate for HR frequency benchmark; not beat/IBI by itself |
| NOMP / sparse spectral reconstruction | sparse periodic components and harmonics | no local implementation | sparse reconstruction paper `eprints.gla.ac.uk/387139/2/387139.pdf` | grid/stop rule and prior frequency bands | exploratory candidate after baseline interface |
| Adaptive notch comb | explicitly suppress fR, 2fR, 3fR | `process_vital_signs_v9.py`, Q=30/Q3=40 | Dai et al. 2025, DOI `10.1088/1361-6501/ad8470` | fR estimate, Q, harmonic count | retain as ablation; prior local net-negative needs re-check under frozen QC |
| Multi-bin / spatial fusion | bin drift, multipath and single-bin false lock | local multi-candidate selection and RGB motion gate | Ubiweb `mmVital`; WMC-VMD camera/radar literature | channel/bin coherence and beamforming geometry | high-priority compatibility audit |
| Beamforming / DBSCAN | spatial target isolation | no canonical implementation | mmCG/Cui literature; TI mmWave labs | calibrated antenna geometry and raw/angle data | conditional; RS6240 data-format compatibility unresolved |
| Template/matched filter | beat timing robustness | official VitalSense route reproduced | VitalSense2024 public repository; Pi-ViMo arXiv `2303.13816` | template leakage and subject split controls | benchmark only with subject-disjoint tuning |
| CEEMDAN, Hampel, phase diff, CFAR, envelope, SPC | denoising/location alternatives | `scripts/experiment_*.py` | historical method A/B | exact historical params/result tables incomplete | retain as historical evidence; do not silently repeat |

External code references: [vmdpy](https://github.com/vrcarva/vmdpy), [mmVital](https://github.com/Ubiweb-lab/mmVital), [TI Resource Explorer](https://dev.ti.com/tirex/explore/), and [radar-heartbeat-detection](https://github.com/seannnnnn1017/radar-heartbeat-detection). Code reuse requires license and commit capture before adoption.
