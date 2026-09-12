# HANDOFF — mmWave integration snapshot v1

- `TASK_ID`: `mmwave_integration_snapshot_v1_closure`
- `STATUS`: `PROVISIONAL_INTEGRATION_READY / PHYSIOLOGY_LIMITED`
- `RUN_ID`: `mmwave_integration_snapshot_v1_20260912_r4`
- `SOURCE_COMMIT`: `16729b2ef245f9304dae8674f3bac433bc02e98c`
- `INITIAL_ARTIFACT_COMMIT`: `62878b88c7025d20bc5a83818447d6b31b7c3bcc`
- `FORMAL_METHOD_COMMIT`: `afa1e869d1ef4e80cf0bb91e910658d0b0efbb91`
- `COHORT`: 116 sessions / 61 participant groups / 2,320 probes
- `AVAILABLE`: 109 sessions / 2,180 probes
- `KEY_GATE`: expected=2,320; observed=2,320; duplicate=0; missing=0; extra=0
- `SCIENCE`: cardiopulmonary HR fused + BR only; both provisional and physiology-limited
- `MOVEMENT_FEATURES`: none; motion proxy is diagnostic-only
- `HRV_STATUS`: `BLOCKED`
- `TIME_CONTRACT`: DLL host receive/enqueue CSV column index 1; Python processing index 2 is QC-only; `[effective_start, probe_onset)`; 30 s nominal; block-truncated
- `TASK_B_SMOKE`: PASS on sub-031/sub-047/sub-099; 60 input probes; 20 complete materialized; duplicate=0; no models trained
- `DOWNSTREAM`: `1.16.10 modality/device migration pending`
- `LOCAL_ONLY`: probe snapshot plus Task B/status/materialized smoke details; hashes recorded in manifest
- `ALGORITHM_CHANGED`: false
- `MODELS_TRAINED`: false
- `OPEN_ISSUES`: #35 and #36 remain open; #41 is the durable integration lane
- `REPLACEMENT`: governed by `MMWAVE_INTEGRATION_SNAPSHOT_V1_REPLACEMENT_CONTRACT.md`
- `CLOUD`: existing Google Drive folder `1eAClViAQxtDGl0jnfb88-ivtYSSH-AXj`; final readback recorded in cloud verification JSON

下游 owner 只能接入 v1 已登记的 HR fused 与 BR 字段，并须先完成 1.16.10 的科学模态/设备分离迁移。不得把设备名当作模态、启用 motion proxy、派生 HRV、训练模型或据诊断结果切换 HR 表示。
