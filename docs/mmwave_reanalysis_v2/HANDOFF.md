# mmWave handoff — competition-bounded route

Status: `TASK3_READY_DEVICE_MATCHED_CALIBRATION`

Branch target: `codex/mmwave-formal-reanalysis-v2`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。毫米波是多模态测量来源之一，不是整个项目的中心。总比赛交付主线见 `docs/canonical/FOCUSWAVE_COMPETITION_DELIVERY_PLAN_V1.md`，执行状态见 `docs/canonical/FOCUSWAVE_COMPETITION_EXECUTION_BOARD_V1.md`。

## 已完成

### Phase 1 / 2A

- 历史资产、数据集、方法、参数、失败模式和外部参考方案已完成证据化整理。
- AgeBalanced 110 participants / 440 total sessions 已对账；当前 benchmark 使用 30 development + 80 held-out participant split。
- ECG/RSP reference、窗口、同步、质量分层、指标、谐波错误和算法比较规则已经确定。
- `per_window_benchmark_v1` JSON Schema 与测试已建立。

### Phase 2B-1

- `ecg_reference_v1` 已实现并通过测试；AgeBalanced development 60/60 Rest sessions 的全程 ECG QC 通过。
- 项目历史方案在 25 s / 5 s 历史等价性条件下，development 60 sessions 的 session-MAE median = **9.14 BPM**；与历史全体 220-session 记录约 9.5 BPM 接近。
- 对 `P003_lying_rest` 的字段级 smoke test 与历史 source commit `f4a8c74d89ec28e005c537cbd5280a15dcb584e1` 完全一致，因此没有证据指向算法转写错误。
- 同一项目历史方案接入统一 30 s / 5 s development benchmark 后：256/268 scored，coverage 95.5%，MAE 26.98 BPM，median AE 13.79 BPM，RMSE 41.13 BPM；这是当前可重复起点，不支持 HR 有效性结论。
- 详情见 `PHASE2B1_HISTORICAL_BASELINE_REPRODUCTION.md`。

## 任务2结果

已执行 `TASK2_EXTERNAL_REFERENCE_SPRINT.md`。SSA+VMD 是唯一允许的外部方案，但其可恢复参数 `SSA L=400` 不适配当前 30 s、10 Hz AgeBalanced 输入（约 300 点）；没有作者代码，也不能自行改 L、补零或改重构秩。因此外部方案在 adapter gate 被 `BLOCKED`，没有生成外部 development score。

结果：项目历史 baseline 仍为 coverage 95.5%、MAE 26.98、median AE 13.79、RMSE 41.13 BPM；SSA+VMD 为 `NOT_RUN / BLOCKED`，不能声称改善或恶化。

任务2给出的 `DOWNGRADE_PHYSIOLOGY` 是**当前产品声明降级**，不是“毫米波永远不能测 HR”的科学结论：当前不能把 HR 作为已验证产品输出，也不再继续做开放式外部算法搜索。

任务2结果与参数审计见 `TASK2_EXTERNAL_REFERENCE_SPRINT_RESULT.md` 和 `configs/mmwave_reanalysis_v2/task2_external_reference_sprint_v1.json`。

## 比赛路线调整

从任务2之后：

1. 不再追完整 220-session 历史等价性；
2. 暂不运行 80 held-out 算法考试，因为没有外部候选值得晋级；
3. 不继续扩展 DR-MUSIC、Harmonic MUSIC、NOMP、CEEMDAN、beamforming 等算法家族；
4. 允许一次**设备匹配校准**，直接回答我们自己的 RS6240 在同步 BIOPAC ECG/RSP 下能否可靠输出 HR 或 BR；
5. HR 与 BR 分开决定；某一个通过不要求另一个也通过；
6. 如果设备匹配校准仍不支持可靠 physiology，则毫米波正式转为 motion / phase / spectral / quality 等 supporting-signal 路线，把剩余时间转给多模态 AI 与心理测量。

## 下一步：任务3

任务文档：`TASK3_RS6240_DEVICE_MATCHED_CALIBRATION.md`

Status: `READY`

目标：在约 1.5–2 小时内，用已有 11 个 RS6240 + BIOPAC 校准 session 做设备匹配验证。

已知资产：

- 11/11 有 raw ECG；
- 10/11 有 raw RSP；
- BIOPAC 约 2000 Hz；
- radar 原始数据约 98–99 fps；
- 2 个 identifier mismatch 必须先核对；
- raw-to-derived 精确映射与部分 BIN hash 仍有缺口，无法证明时应跳过而不是猜测。

任务3只允许四种产品决定：

- `KEEP_HR_AND_BR`
- `KEEP_HR_ONLY`
- `KEEP_BR_ONLY`
- `SUPPORTING_SIGNAL_ONLY`

主线程建议 GPT-5.6 Terra / medium；默认不使用 Sol/high。

## 当前禁止事项

- 不再接入新的外部算法家族；
- 不看 AgeBalanced 80 held-out；
- 不跑完整 220-session 历史等价性；
- 不访问正式 `J:\Data` cohort；
- 不为了保留 physiology 放宽 ECG/RSP reference、QC 或评价门槛；
- 不恢复 HRV，除非逐搏验证作为自然副产物已经明确通过；
- 不让毫米波阻塞 Behavior、NIR/RGB、AI、信效度主线。

任务3完成后必须停止，等待是否进入正式数据提取的下一轮决定。
