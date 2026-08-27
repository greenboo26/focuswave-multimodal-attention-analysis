# 毫米波任务3：RS6240 + BIOPAC 设备匹配校准

Status: `READY`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。

## 1. 这一轮在做什么

Task 2 已经停止外部 SSA+VMD 路线，因为公开可恢复参数与当前 30 s / 10 Hz 输入不兼容。下一步不再继续找更多外部算法，而是直接回答最贴近产品的问题：

> **我们自己实际使用的 RS6240，在同步 BIOPAC ECG/RSP 金标准下，到底能不能可靠输出 HR 或 BR？**

这是毫米波 physiology 路线的最后一个高收益检查。HR 与 BR 分开判断，不要求两者一起通过。

## 2. 为什么现在做

AgeBalanced 只提供 ECG，没有 RSP，而且项目历史方案在统一 30 s development 条件下 HR 表现较差。继续做更多外部算法复现的比赛收益已经不足。

本项目已有设备匹配校准资产：

- 11 个 RS6240 校准 session；
- 11/11 有 raw ECG；
- 10/11 有 raw RSP；
- BIOPAC 参考采样约 2000 Hz；
- radar 原始数据约 98–99 fps；
- 其中存在 2 个 identifier mismatch，需要在评分前核对；
- raw-to-derived 精确映射与部分 BIN hash 仍有缺口。

因此这一轮优先验证自己的设备，而不是继续做论文算法擂台。

## 3. 时间上限

本轮建议 **1.5–2 小时**，计入毫米波约 10 小时总预算。

建议节奏：

1. 0–20 min：确认 11 个 session 的 ECG/RSP/radar/timestamp 对应关系，两个 ID mismatch 无法证实时跳过，不强行修正；
2. 20–45 min：复用既有 ECG/RSP reference 规则和项目历史 RS6240 处理链，完成最小 adapter；
3. 45–90 min：运行 HR 与 BR 设备匹配评分；
4. 90–120 min：失败模式分析并给出产品角色决定。

若数据对应关系在前 20–30 min 无法可靠确定，允许 `PARTIAL/BLOCKED` 提前停止，不为完成任务猜测身份或时间对齐。

## 4. 数据与方法边界

本轮允许：

- 已登记的 11 个 RS6240 + BIOPAC 校准目录；
- raw ECG；
- raw RSP（10/11）；
- radar 原始/已验证派生入口；
- source timestamps；
- 既有项目历史 RS6240 方案和简单 transparent baseline；
- 30 s / 5 s 作为产品主窗口；
- 60 s / 5 s 仅作为 BR/低频稳定性 sensitivity；
- 既有 reference QC、coverage、MAE、median AE、RMSE、相关、Bland–Altman、quality strata。

本轮禁止：

- 不再接入新的外部算法家族；
- 不看 AgeBalanced 80 held-out；
- 不访问正式 `J:\Data` cohort；
- 不修改既定 ECG/RSP reference 规则来追求更好结果；
- 不根据 ECG/RSP 真值逐窗口调 radar 参数；
- 不把 accelerometer 或 radar respiration 重命名为 RSP；
- 不恢复 HRV，除非逐搏验证作为自然副产物已经明确达到既有 gate；
- 不为了保留 physiology 强行放宽阈值。

## 5. HR 与 BR 分开验收

### HR

至少报告：

- participant/session/window coverage；
- MAE / median AE / RMSE；
- Pearson / Spearman；
- Bland–Altman bias / LoA；
- 2x / 0.5x 锁频；
- 在有 RSP 的 session 上检查疑似 respiratory harmonic 锁定；
- high / medium / low quality 分层。

### BR

10 个有 RSP 的 session 单独评分，至少报告：

- coverage；
- MAE / median AE / RMSE；
- correlation；
- Bland–Altman；
- quality strata；
- 30 s 主窗口与 60 s sensitivity 的差异。

BR 不因 HR 失败而自动失败，HR 也不因 BR 失败而自动失败。

## 6. 产品决策只允许四种

- `KEEP_HR_AND_BR`：HR、BR 都有足够证据，可进入后续正式数据提取；
- `KEEP_HR_ONLY`：只保留 HR 生理解释，BR 降级；
- `KEEP_BR_ONLY`：只保留 BR 生理解释，HR 降级；
- `SUPPORTING_SIGNAL_ONLY`：HR、BR 都不足以支持产品生理声明，毫米波只保留 motion / phase / spectral / quality 等信号级支持特征。

无论哪种，都不能因为比赛需要而把未通过的变量包装成“已验证”。

## 7. 对后续比赛主线的影响

若 HR 或 BR 至少一个保留：

- 后续只把通过的 physiology 变量接入正式 `J:\Data`；
- 与 Behavior/NIR/RGB 做相同 folds 的增量分析；
- 判断是否真正增加心理测量价值。

若 `SUPPORTING_SIGNAL_ONLY`：

- 停止毫米波 physiology 研发；
- 不再安排 held-out 算法考试；
- 正式数据只提取已有 evidence 支持的 signal-level 特征与 quality；
- 把剩余时间转给多模态 AI、问卷效度和产品评分。

## 8. 模型路由

主线程：**GPT-5.6 Terra / medium**。

允许 Luna/low 处理：

- session/文件对账；
- hash/schema/test；
- 机械汇总。

只有当出现“同一数据在两套合理生理判定下产生矛盾结论”或“是否足以支持产品生理有效性声明”这类关键判断时，才短暂升级 **GPT-5.6 Sol / medium**。

默认不使用 Sol/high。

## 9. 交付物

必须产生：

- 最终可评分 session manifest；
- 两个 ID mismatch 的处理证据；
- HR 结果表；
- BR 结果表；
- 主要失败模式；
- `KEEP_HR_AND_BR / KEEP_HR_ONLY / KEEP_BR_ONLY / SUPPORTING_SIGNAL_ONLY` 明确结论；
- 对后续正式数据可输出变量的建议；
- commit SHA；
- `PASS / PARTIAL / BLOCKED`。

任务3完成后停止，不自动进入正式 `J:\Data`、多模态模型或 HRV。
