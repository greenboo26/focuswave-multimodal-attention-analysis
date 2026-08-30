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
- **RESTORE_EXISTING**：historical physical gate/target contract、previous-BPM selector continuity、segment correction/consensus、final signal/QC output chain。previous anchor 与 time/frequency fusion 已在同一 323 窗直接重放；其余链段只有 bundled comparison，不能宣称单阶段因果贡献。
- **UNPROVEN**：near-field peak 已被 static/clutter suppression 去除；DC/static stage 的独立收益；VMD、harmonic guard、segment correction/consensus、final QC 的独立收益；candidate persistence。
- **DROP**：new selector/new algorithm、ECG-informed gate tuning、tail repair、按 20 s vs 60 s MAE 直接推广窗口。#25 保持 `WAIT_ON_SELECTOR_VALIDITY`。

## 逐步人话解释

| 步骤 | 代码做什么 | 为什么 | 项目内效果 | 参考/依据 | 当前决策 |
|---|---|---|---|---|---|
| S01 输入 | 把 NPZ 的 8 个复数通道按 range bin 叠成数据立方体，不做第二次 Range FFT | 保留设备已经输出的距离域信息 | 形状/打包审计通过；没有单独 MAE 归因 | `process_vital_signs_v3_1_1.py:1099-1112` | KEEP |
| S02 候选 | 用平均功率、相位稳定性和频带分数列出可能的 bin/channel | 先回答哪里有可用动态信号 | target 会改变下游结果，但与后续步骤 bundled | `process_vital_signs_v3_1_1.py:1146-1233` | RESTORE_EXISTING |
| S03 距离门 | 历史链将 0.30–1.50 m 固定为 bins 9–40；当前 targeted 独立选择未使用它 | 排除物理上不合理的候选 | 既有 gate/target ablation 保留同一控制口径 | 0.037 m/bin 历史 lineage；既有 gate ablation | RESTORE_EXISTING |
| S04 静态项 | 审计确认选 bin 前仍使用 raw mean-power；绘图减均值不回写选择 | 区分真实去杂波和仅用于显示的处理 | 没有可复用的 pre-selection A/B | `process_vital_signs_v3_1_1.py:1146-1172` 与审计矩阵 | UNPROVEN |
| S05 相位 | 对选中复数样本取 angle、unwrap，再换算位移 | 从微小相位变化得到运动信号 | 为三条路径共享；无独立归因 | `process_vital_signs_v3_1_1.py:268-270,1415-1439` | KEEP |
| S06 带通 | 用既有 SOS 带通分开 BR/HR；VMD 是另一个已有分支 | 去掉带外成分 | bandpass 共享；VMD 没有当前 20 s 可切换输出 | `process_vital_signs_v3_1_1.py:273-394,1296-1369` | KEEP bandpass / UNPROVEN VMD |
| S07 窗口 | 历史链有 course/segment 结构，targeted 固定为 20 s | 让短窗估计有上下文 | historical 20 s adaptation 优于 block-local，但与窗口定义纠缠 | 既有 same-window estimator audit | RESTORE_EXISTING（bundle） |
| S08 频谱 | 做 Hann periodogram、峰候选和时域峰候选 | 产生 HR 假设 | fixed periodogram→selector 可直接比较 | `process_vital_signs_v3_1_1.py:727-775,1236-1241` | KEEP |
| S09 折叠 | 按已有 half/double/triple 规则处理谐波关系 | 避免倍频/半频误锁 | replay 没有折叠前候选列表，不能安全做一开关 A/B | `process_vital_signs_v3_1_1.py:713-724,1800-1944`；REUSE_REJECTION_REASON | UNPROVEN |
| S10 连续性 | 用上一窗 BPM 给候选打锚点并跨窗传递 | 限制不合理跳变 | MAE 24.902438→13.276285；同窗 245/323 更好 | `_select_spectral_bpm()` 与 selector replay | RESTORE_EXISTING |
| S11 段校正/共识 | 对 segment 结果做校正、聚类、中位数/融合 | 抑制孤立 segment 错误 | 只观察到 full-chain bundled gain；没有 correction-only 中间表 | `process_vital_signs_v3_1_1.py:1947-2239`；REUSE_REJECTION_REASON | RESTORE_EXISTING（bundle） |
| S12 最终门控 | 合并时域/频域、计算质量分并输出 QC；缺失保持缺失 | 控制最终输出可信度边界 | targeted old path 未暴露同契约门控前值，不能拆 QC-only delta | `process_vital_signs_v3_1_1.py:2092-2313,2379-2497`；REUSE_REJECTION_REASON | RESTORE_EXISTING（bundle） |
| S13 ECG | 只在 mmWave 输出之后读取 ECG eligibility/HR 作 oracle | 固定评估分母而不调参 | COMPLETE∩ECG_VALID=323；ECG 未进入选择 | #24 contract | KEEP |

## 证据文件

- `MMWAVE_PIPELINE_STAGE_EVIDENCE_2026-08-30.csv`：逐阶段代码位置、输入输出、用途、三路径是否使用、直接效果证据、文献支持与决策。
- `MMWAVE_PIPELINE_STAGE_ABLATION_METRICS_2026-08-30.csv`：323-window fixed control 的 MAE/median AE/bias/RMSE/Pearson/Spearman/valid n。
- `MMWAVE_PIPELINE_STAGE_ABLATION_PAIRWISE_2026-08-30.csv`：同窗 paired delta。
- `MMWAVE_FAILURE_LOCUS_SUMMARY_2026-08-30.csv`：102 wrong / 182 nearby 的恢复数与剩余定位边界。
- `MMWAVE_HISTORICAL_PRODUCER_LINEAGE_2026-08-30.csv`：3.777 lineage、commit、参数、输入、输出绑定。
