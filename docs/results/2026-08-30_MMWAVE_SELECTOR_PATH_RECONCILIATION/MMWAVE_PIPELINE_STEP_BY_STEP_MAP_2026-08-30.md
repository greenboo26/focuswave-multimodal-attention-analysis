# mmWave producer lineage and step-by-step map (2026-08-30)

## 固定事实

- 历史最佳 HR≈3.7772146 bpm 的完整 lineage：`run_hr_course_99_corrected.py` → `process_vital_signs_v3_1_1.py`，commit `64634159d226ee1ed892d53e56fcf3697fbff9b8`。
- 输入是 8-channel complex range-domain DataCube，不是 raw ADC；历史 target 先在前 6000 frames 选择，再固定到完整记录。
- 历史物理 gate 为 `0.30–1.50 m = bins 9–40`（按 0.037 m/bin）；current targeted independent selector 没有使用该 gate。
- 历史、current formal、targeted 三条路径都没有被证实在 target selection 前执行 DC/static/clutter suppression；绘图中的减均值仅是 display diagnostic。
- 本轮控制口径固定为 coverage `COMPLETE` 且 ECG `ECG_VALID`，即 323 windows；`97795/block4/w027,w028` 排除，不 padding/backfill/reconstruct，24,809 ms tail 只保留 provenance。

## 顺序图

`complex range cube` → `raw range-power profile/candidates` → `[historical gate only: bins 9–40]` → `bin/channel target` → `phase angle → unwrap → displacement` → `BR/HR bandpass` → `periodogram/FFT + time peaks` → `harmonic fold` → `previous-BPM continuity` → `segment correction/consensus` → `time/frequency fusion + signal gate` → `HR/BR output` → `ECG oracle evaluation only`

## 路径差异

1. **历史 producer**：6000-frame fixed target + historical gate + `bp_heart` + full v3.1.1 downstream chain + 60 s historical probe.
2. **current formal producer**：调用同一 `process_vital_signs_v3_1_1.py` full path，caller gate 作用于 BR/HR candidate set；默认 runner 未传 external RSP acquisition input。
3. **old targeted path**：per-window raw target selection/local ±3-bin continuity + bandpass/periodogram/peak；没有接入 existing `_select_spectral_bpm`、VMD/full historical segment correction/consensus/time-course chain。
4. **本轮 restored replay**：固定已有 target，接回 existing spectral selector、previous-BPM state、harmonic folding and time/frequency fusion；这是 supporting replay，不是新 selector，也不把 ECG 传入选择。

## 可验证决策

- **KEEP**：complex input semantics、phase extraction、bandpass、periodogram/peak、ECG oracle-only denominator。
- **RESTORE_EXISTING**：historical physical gate/target contract、previous-BPM selector continuity、segment correction/consensus、final signal/QC output chain。先按已有实现接回并测量。
- **UNPROVEN**：near-field peak 已被 static/clutter suppression 去除；DC/static stage 的独立收益；VMD、harmonic guard 的独立收益；candidate persistence。
- **DROP**：new selector/new algorithm、ECG-informed gate tuning、tail repair、按 20 s vs 60 s MAE 直接推广窗口。#25 保持 `WAIT_ON_SELECTOR_VALIDITY`。

## 证据文件

- `MMWAVE_PIPELINE_STAGE_EVIDENCE_2026-08-30.csv`：逐阶段代码位置、输入输出、用途、三路径是否使用、直接效果证据、文献支持与决策。
- `MMWAVE_PIPELINE_STAGE_ABLATION_METRICS_2026-08-30.csv`：323-window fixed control 的 MAE/median AE/bias/RMSE/Pearson/Spearman/valid n。
- `MMWAVE_PIPELINE_STAGE_ABLATION_PAIRWISE_2026-08-30.csv`：同窗 paired delta。
- `MMWAVE_FAILURE_LOCUS_SUMMARY_2026-08-30.csv`：102 wrong / 182 nearby 的恢复数与剩余定位边界。
- `MMWAVE_HISTORICAL_PRODUCER_LINEAGE_2026-08-30.csv`：3.777 lineage、commit、参数、输入、输出绑定。
