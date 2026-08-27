# mmWave handoff — competition-bounded route

Status: `TASK2R_COMPLETED_PARTIAL_DOWNGRADE_PHYSIOLOGY`

Branch target: `codex/mmwave-formal-reanalysis-v2`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。毫米波是多模态测量来源之一，不是整个项目的中心。总比赛交付主线见 `docs/canonical/FOCUSWAVE_COMPETITION_DELIVERY_PLAN_V1.md`，执行状态见 `docs/canonical/FOCUSWAVE_COMPETITION_EXECUTION_BOARD_V1.md`。

## 已完成

### Phase 1 / 2A

- 历史资产、数据集、方法、参数、失败模式和外部参考方案已整理。
- AgeBalanced 110 participants / 440 total sessions 已对账；30 development + 80 held-out participant split 保留。
- ECG reference、质量、同步、指标和 held-out 使用规则已确定。

### Phase 2B-1

- `ecg_reference_v1` 已实现并通过测试；development 60/60 Rest sessions 全程 ECG QC 通过。
- 项目历史方案在 25 s / 5 s 历史等价条件下，development 60 sessions 的 session-MAE median = **9.14 BPM**；接近历史全体 220-session 约 9.5 BPM。
- P003 字段级 smoke test 与历史 source commit `f4a8c74d89ec28e005c537cbd5280a15dcb584e1` 一致，没有证据表明算法转写错误。
- 同一项目历史方案在 30 s / 5 s product-window development 条件下：coverage 95.5%，MAE 26.98 BPM，median AE 13.79 BPM，RMSE 41.13 BPM。

注意：9.14 与 26.98 来自不同窗口、不同 ECG 评分/聚合口径，不能直接解释为“算法突然差了三倍”。

## 原 Task 2 的结论如何解释

原 Task 2 仅允许 30 s / 10 Hz 输入。SSA 公开参数要求 `L=400`，而30 s只有约300点，因此 SSA+VMD 在该输入条件下无法按公开参数直接运行，任务状态为 `BLOCKED`。

这个结论仍然保留，但含义仅限于：

> **论文原参数与30 s输入不兼容。**

它不等于：

- SSA+VMD 已被证明效果差；
- 外部算法不值得验证；
- 项目毫米波 HR 已经被科学判死。

## 当前路线：双轨窗口

### 30 s 产品轨道

- FocusWave 产品/主分析仍以 30 s 为主要时间窗口；
- 30 s 结果用于回答“产品如果按这个时间尺度更新，算法是否可用”；
- 不因为外部论文需要50 s就修改产品主窗口。

### 50 s AgeBalanced 外部方法轨道

- AgeBalanced 是外部验证数据；
- 新增 50 s / 5 s method-native comparison，使 50 s × 10 Hz ≈ 500 点，可按 SSA `L=400` 运行；
- 项目历史方案和 SSA+VMD 都必须使用同一 50 s、同一 development 30 人、同一 ECG reference 比较；
- 50 s 输出单独标记为 external method comparison，不能冒充30 s产品性能。

任务文档：`TASK2R_EXTERNAL_REFERENCE_50S_CONTINUATION.md`。

## 80 held-out 的角色

80 人没有取消。只有在 50 s development 完成后，若至少一个方案具备现实外部泛化价值，才进入80人。

进入80前必须已经确定：

- 外部实现规则；
- 项目方案50 s配置；
- SSA/VMD关键参数与选择规则；
- 评价指标与比较方式。

之后两种方案可在同一80人上按确定后的50 s条件一次性比较。不能看完80结果后再调整方法并继续把80称为 untouched held-out。

## 本地 RS6240 + BIOPAC 重新定位

已核对 `kyandi233-dev/FocusWave@ecg`：

- `02-tools/11-calibrate-mmwave-ecg.py`：静息5min → 深呼吸2min → 屏息45s → 静息5min，专门用于 HR/HRV/呼吸谐波机制校准；
- `02-tools/12-test-breath-focus.py`：同一被试机械按键 vs 专注 SART 交替，专门区分“呼吸率锁低是算法问题还是真实专注/屏息现象”；
- 两者明确不同于正式实验。

因此本地 BIOPAC 数据后续只作为**设备/机制/压力测试证据**，不能替代 AgeBalanced 多被试 ECG 外部泛化证据，也不能把多个 session 当多个独立被试。

原 `TASK3_RS6240_DEVICE_MATCHED_CALIBRATION.md` 暂缓，不再作为当前下一步，也不再承担“产品级生理资格最终判决”的角色。

## 当前下一步

执行 `TASK2R_EXTERNAL_REFERENCE_50S_CONTINUATION.md`：

1. 只用 AgeBalanced development 30 人；
2. 50 s / 5 s；
3. 项目历史方案 + SSA+VMD 同条件运行；
4. 不看80；
5. 不访问 `J:\Data`；
6. 不扩第二个外部算法家族；
7. 完成后只决定是否值得进入80 held-out。

主线程建议 GPT-5.6 Terra / medium；默认不使用 Sol/high。

## Task 2R 结果

- 已在 30 development participants / 60 Rest sessions 上完成 50 s / 5 s 同条件比较。
- 项目历史方案：81/88 scored，coverage 92.05%，MAE 29.02、median AE 15.03、RMSE 43.10 BPM。
- SSA+VMD `paper_reimplementation/adapted`：81/88 scored，coverage 92.05%，MAE 28.12、median AE 15.74、RMSE 41.72 BPM；MAE 改善 0.90 BPM，但未达到 HR gate，锁频总数未下降。
- 推荐 `DOWNGRADE_PHYSIOLOGY`；50 s 不作为 30 s 产品 claim，任务完成后停止，不自动进入 80 人。
- 详见 `TASK2R_EXTERNAL_REFERENCE_50S_RESULT.md`。
