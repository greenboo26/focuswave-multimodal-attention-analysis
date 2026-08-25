# 厚粲杯项目当前状态

更新时间：2026-08-26

## 当前科研状态

- C1 逐搏 IBI/HRV 线在本比赛周期内已封存。当前正式状态为 `C1_ALIGNMENT_NOT_PRIMARY_CAUSE_STOP_HRV_CONFIRMED`；不再扩大 lag 搜索，不开发新的逐搏检测器。
- C2 心理状态预测仍是毫米波主线。既有 calibration-free absolute mmWave baseline 不构成“毫米波无效”结论；后续重点是个体内/静息校准后的增量价值。
- Q1 问卷外部效标分析已完成。北京 canonical 主分析纳入 67 个 session、46 个重复被试组；正式问卷第 4 题“整个实验过程中走神时间比例”与 label 1 完全任务聚焦比例 Spearman rho = -0.581，95% CI [-0.735, -0.409]；与 commission error rate rho = 0.260，95% CI [0.014, 0.494]。该结果构成较强 probe 一致性和较弱行为效标支持。
- 北京—珠海正式实验协议关系已确认，正式裁决见 `docs/decisions/2026-08-26-beijing-zhuhai-protocol-identity-harmonization.md`。

## 北京—珠海正式协议

- 珠海正式实验自 2026-08-15 开始，使用 BBB 三个正式 Block。
- 北京正式实验是同一正式协议的 BB 缩短版。
- formaltest 历史中曾出现 1–9 分即时专注评分的过渡版本，但该版本从未用于正式被试，不进入正式数据版本划分。
- 两地正式实验的 B1/B2、四分类注意状态探针、警觉度探针和 probe schedule family 属于同一 measurement protocol。
- 共同主分析范围：`Beijing B1+B2 + Zhuhai B1+B2`。
- 珠海 B3：`long time-on-task extension`，单独作为更长时程扩展分析。
- pooled 分析必须保留 `site`，participant/repeat participant 仍为独立分组单位。

## 珠海预实验与重复参与规则

- 珠海正式实验前约有 10 名左右预实验被试；预实验使用 FocusWave 中单独标注的预实验程序分支，程序结构与正式实验差异较大。
- 预实验 session 不直接并入正式 B1/B2/B3 probe-level 主分析。
- 北京和珠海正式实验均允许同一自然人最多参加 3 次正式实验。
- 若同一自然人出现 4 个及以上 session，必须逐场判断是否为：预实验、质量问题后的重采、或真正有效的正式重复实验。不能按 session 数量机械定义正式参加次数。
- canonical 身份层必须区分 `phase=pilot/formal`、`is_retake`、`formal_repeat_index`、`repeat_participant_id` 和程序版本/protocol family。

## 问卷身份辅助题处理

- 珠海正式问卷比北京多一个“是否参加过第一阶段/预实验”的问题，用于辅助识别预实验参与经历。
- 北京只有最前几个答卷曾残留该题，发现后即从问卷删除；北京该题回答后续直接忽略，不进入问卷分析。
- 珠海该题只作为 participant/session provenance 和 pilot/formal linkage 辅助字段，不作为心理测量变量，不进入专注状态预测特征。

## 当前直接下一步

1. 建立北京—珠海统一 canonical person/session crosswalk，先区分 pilot / formal / retake / formal repeat 1–3。
2. 建立 `shared_primary = Beijing B1+B2 + Zhuhai B1+B2` 的共同 probe master。
3. 建立 `zhuhai_extended = Zhuhai B3` 的长时程扩展 master。
4. 在共同协议数据上先验证行为/探针纵向规律和 site × progress，再决定后续 pooled 传感器模型。

## 解释边界

- 珠海预实验与正式实验属于不同 protocol family；身份可以连接，测量数据不能未经定义直接拼接。
- 同一自然人可以跨预实验、正式实验和重采出现多个 session；自然人身份与有效正式重复次数必须分开记录。
- Q1 是 session-level 外部效标支持，不等于逐窗口标签的完全验证。
- C1 的停止结论仅适用于当前比赛周期的逐搏 IBI/HRV 开发，不代表 RS6240 永远无法测量 HRV。
