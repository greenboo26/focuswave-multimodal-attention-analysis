# 毫米波任务2：单一外部参考方案限时比较

Status: `COMPLETED_BLOCKED_EXTERNAL_REFERENCE`

Dispatched: 2026-08-27

Completed: 2026-08-27

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。

## 1. 这一轮在做什么

不是继续做开放式毫米波算法研究，而是在已经可运行的 AgeBalanced development benchmark 上，回答一个比赛层面的实用问题：

> 项目历史方案目前最大的已知问题是呼吸谐波/错误频率锁定。引入一个成熟外部方案，能否在有限时间内带来足够明显、可重复的改进，值得进入最终比较？

本轮只允许接入 **1 个主要外部参考方案**。

首选：**SSA + VMD / EE-PCC-VMD 路线**。

选择理由：

- 直接针对噪声、模态混叠和呼吸谐波进入心率频带的问题；
- 本项目已有 VMD 历史实现与 SSA A/B 证据，可复用资产较多；
- 相比 DR-MUSIC，参数和工程接入负担更低，更符合比赛限时目标；
- 当前方法矩阵已把它列为 high-priority reproduction candidate。

如果关键论文参数、输入假设或实现证据无法在短时间内恢复，不得自行发明参数；标记 `BLOCKED/PARTIAL` 后停止，不切换去做一长串其他算法。

## 2. 为什么现在做

Phase 2B-1 已经完成：

- ECG reference v1：PASS；
- 30 人 development / 60 Rest sessions 的 25 s 历史等价性诊断：session-MAE median 9.14 BPM，接近历史全体 220-session 约 9.5 BPM；
- 项目历史方案在统一 30 s / 5 s development 条件下可运行，但表现较差：256/268 scored，coverage 95.5%，MAE 26.98 BPM，median AE 13.79 BPM，RMSE 41.13 BPM；
- 没有证据表明历史算法转写错误；P003 五个 25 s 窗口字段级 smoke test 与历史 source commit 完全一致。

因此没有必要继续消耗比赛时间追完整 220-session 历史复现。当前更有价值的是：看一个针对主要失败模式的成熟外部方法是否能明显改善 development 表现。

## 3. 输入与比较对象

### A. 项目历史方案

来源：`f4a8c74d89ec28e005c537cbd5280a15dcb584e1` 对应的 AgeBalanced historical pipeline，经当前 adapter 接入 30 s / 5 s benchmark。

当前 development 起点：

- coverage 95.5%；
- MAE 26.98 BPM；
- median AE 13.79 BPM；
- RMSE 41.13 BPM。

### B. 简单基准方案

仅当现有 dual-band adapter 可以直接复用时纳入；不得为了补这个对照额外花大量开发时间。

### C. 外部参考方案

首选 SSA + VMD / EE-PCC-VMD。必须记录：

- 来源论文/仓库；
- 是否官方实现、仓库实现或 paper reimplementation；
- commit/license；
- 关键参数来源；
- 与 AgeBalanced 输入格式的适配说明；
- 哪些部分是原方法，哪些是本项目适配层。

## 4. 数据边界

本轮只允许：

- AgeBalanced development 30 participants；
- 两个 Rest session / participant；
- 30 s / 5 s 主窗口；
- ECG reference v1；
- 现有统一逐窗口 schema 和现有评价指标。

本轮禁止：

- 不看 80 held-out participants；
- 不跑完整 220-session 历史等价性；
- 不访问正式 `J:\Data`；
- 不做 BR；
- 不恢复 HRV；
- 不因为候选结果不好而修改既定 ECG reference、QC、评价指标或 split；
- 不扩展到 NOMP、CEEMDAN、beamforming、多个 MUSIC 变体等开放式方法搜索。

## 5. 时间上限

本轮按比赛收益设置约 **2.5 小时分析/实现预算**，而不是追求论文级完整复现。

建议内部节奏：

1. 0–30 min：恢复 SSA+VMD 最关键参数、来源和已有可复用资产；
2. 30–90 min：完成最小可运行 adapter + synthetic/smoke test；
3. 90–130 min：运行 development 30 人并生成统一结果；
4. 130–150 min：差异分析、形成是否值得继续的明确建议。

若实现条件不满足，优先提前停止并报告证据缺口，不得为“完成任务”编造参数。

## 6. 本轮要回答的问题

至少回答：

1. SSA+VMD 在 development 30 人上是否比项目历史方案降低 HR 误差？
2. 是否减少明显 2x/0.5x/疑似呼吸谐波错误？若 AgeBalanced 无 RSP，respiratory harmonic 只能报告 `NOT_ASSESSABLE`，不能伪装成 0。
3. 改进是否靠牺牲大量 coverage 得到？
4. high/medium/low quality strata 是否出现一致趋势？
5. 是否达到既定 HR validation gate；若未达到，离门槛还有多远？
6. 该方法的实现与参数是否足够可复现，值得进入 80 人最终比较？

不要求为了得到“赢家”而继续调到满意。

## 7. 决策规则

任务2结束只做三类建议：

- `ADVANCE`：外部参考方案有明确、可复现的 development 改善，coverage 无明显崩塌，值得进入下一步；
- `KEEP_PROJECT_ROUTE`：没有足够改进，保留项目历史方案/现有信号级路线，不继续扩算法家族；
- `DOWNGRADE_PHYSIOLOGY`：两条路线都不足以支持可靠 HR 生理解释，应优先把毫米波定位为 supporting signal，后续时间转给多模态 AI 和心理测量验证。

这不是为了选“世界最强算法”，而是为了在比赛时间内决定毫米波在 FocusWave 产品中的合理角色。

## 8. 模型路由

主线程：**GPT-5.6 Terra / medium**。

允许 Luna/low 子代理处理：

- 文件/manifest 对账；
- schema/test；
- 机械参数摘录与文档一致性检查。

仅在以下情况短暂升级 GPT-5.6 Sol / medium：

- 项目方案与外部方案出现无法解释的重大科学冲突；
- 必须决定是否修改既定科学规则；
- 需要判断某结果是否足以支撑生理有效性声明。

默认不使用 Sol/high。

## 9. 交付物

必须产生：

- 外部参考方案 adapter/config；
- provenance + 参数来源记录；
- development-only 统一结果；
- 与项目历史方案的同表比较；
- 主要失败模式摘要；
- 对 `ADVANCE / KEEP_PROJECT_ROUTE / DOWNGRADE_PHYSIOLOGY` 的明确建议；
- commit SHA；
- `PASS / PARTIAL / BLOCKED` 状态。

任务2完成后停止，不自动进入 80 人 held-out、RS6240 正式校准或 `J:\Data`。
