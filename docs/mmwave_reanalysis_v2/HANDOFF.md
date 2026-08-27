# mmWave handoff — competition-bounded route

Status: `READY_TASK2_COMPETITION_SPRINT`

Branch target: `codex/mmwave-formal-reanalysis-v2`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。毫米波是多模态测量来源之一，不是整个项目的中心。总比赛交付主线见 `docs/canonical/FOCUSWAVE_COMPETITION_DELIVERY_PLAN_V1.md`。

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

## 比赛路线调整

不再把“完整重跑 220-session 历史等价性”作为默认下一步。原因：

1. Phase 2B-1 已足以证明历史方案与历史代码链可以对上；
2. 完整 220-session 只会进一步追历史聚合细节，比赛收益较低；
3. 当前更重要的是在有限时间内判断：一个成熟外部方案能否明显改善项目历史方案的主要失败模式；
4. 毫米波从当前阶段起受约 10 小时总研究/完善上限约束，后续时间必须为多模态 AI、心理测量信效度和产品交付让路。

## 下一步：任务2

执行 `TASK2_EXTERNAL_REFERENCE_SPRINT.md`。

目标：只在 AgeBalanced development 30 participants 上，接入 **1 个**高价值外部参考方案并与项目历史方案比较。

首选：SSA + VMD / EE-PCC-VMD 路线，因为它直接针对噪声、模态混叠和呼吸谐波问题，同时能最大化复用本项目已有 VMD/SSA 资产。

任务2约 2.5 小时预算；主线程 GPT-5.6 Terra / medium。机械 schema/test/对账可用 Luna/low；默认不使用 Sol/high。

## 任务2禁止事项

- 不看 80 held-out participants；
- 不跑完整 220-session 历史等价性；
- 不访问正式 `J:\Data`；
- 不做 BR；
- 不恢复 HRV；
- 不扩展成多个算法家族的开放搜索；
- 不因为候选结果不好而重新改 ECG reference、QC、split 或评价指标。

## 任务2结束时必须给出

- development 同表比较；
- 外部方法 provenance/参数来源；
- 是否降低 HR 误差、错误锁频以及是否牺牲 coverage；
- `ADVANCE / KEEP_PROJECT_ROUTE / DOWNGRADE_PHYSIOLOGY` 三选一建议；
- commit SHA；
- `PASS / PARTIAL / BLOCKED`。

任务2完成后停止，不自动进入 80 人最终比较、RS6240 校准或正式 `J:\Data`。
