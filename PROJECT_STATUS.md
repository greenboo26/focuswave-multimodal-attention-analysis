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
- 珠海 B3：`long time-on-task extension`。
- pooled 分析保留 `site`，participant/repeat participant 作为独立分组单位。

## 珠海预实验与重复采集规则

- 珠海正式实验前约有 10 名左右预实验被试；预实验使用 FocusWave 中单独标注的预实验程序分支，程序结构与正式实验差异较大。
- 预实验 session 作为独立 protocol family 保存，可用于 pilot-specific 分析、流程质控和身份层纵向关联；正式主分析使用 formal protocol 数据。
- 常规每人最多安排 3 次正式实验是采集管理规则，用于避免同一早晨/下午/晚上短时间连续重复，不是统计有效性的硬性上限。
- 因毫米波、NIR 或其他模态质量问题进行的第 4 次及以后正式重采可以保留，只要核心任务、probe 和时间线有效。
- 数据质量按模态判断：某一模态质量不足时，该 session 的其他有效模态、行为、probe 和问卷继续用于相应分析。
- canonical 身份层记录 `phase`、`formal_session_index`、`collection_reason`、`repeat_participant_id`、程序版本和各模态 usable 字段。
- 同一自然人的全部 session 在机器学习评估中进入同一个 participant group。

## 问卷身份辅助题处理

- 珠海正式问卷比北京多一个“是否参加过第一阶段/预实验”的问题，用于辅助识别预实验参与经历。
- 北京只有最前几个答卷曾残留该题；北京该题回答后续直接忽略。
- 珠海该题只作为 participant/session provenance 和 pilot/formal linkage 辅助字段，不作为心理测量变量，不进入专注状态预测特征。

## 当前直接下一步

1. 建立北京—珠海统一 canonical person/session crosswalk，逐 session 标记 pilot/formal、formal_session_index、collection_reason 和 program_family。
2. 为每个正式 session 建立 `behavior/probe/mmwave/NIR/RGB` 模态级 QC，而不是整场一票剔除。
3. 建立 `shared_primary = Beijing B1+B2 + Zhuhai B1+B2` 的共同 probe master。
4. 建立 `zhuhai_extended = Zhuhai B3` 的长时程扩展 master。
5. 先运行共同协议的行为/probe 纵向验证与 `site × progress`，随后将同一 canonical master 接入毫米波/NIR/RGB matched-cohort 模型。
6. 对第 4 次及以后正式 session 在主分析中保留，并预先准备“全部有效 session vs 每人最多前三场”的敏感性分析。

## 解释边界

- 珠海预实验与正式实验属于不同 protocol family；身份可以连接，正式 pooled probe 主分析使用 formal protocol。
- 正式 session 是否保留由核心实验结构决定；具体模态是否进入某一分析由该模态 QC 决定。
- Q1 是 session-level 外部效标支持，不等于逐窗口标签的完全验证。
- C1 的停止结论仅适用于当前比赛周期的逐搏 IBI/HRV 开发，不代表 RS6240 永远无法测量 HRV。
