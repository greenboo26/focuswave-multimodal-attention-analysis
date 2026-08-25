# D1 北京—珠海 Canonical 字段与估计门槛

入口：`scripts/run_d1_beijing_zhuhai_canonical_harmonization.py`。

| 输出字段 | 规则 |
| --- | --- |
| `repeat_participant_id` | 唯一的参与者聚类键；不得以 probe 行替代自然人独立样本。 |
| `session_id` | 仅在确定性实际 session 映射后填写。珠海登记行可为空。 |
| `phase` | 北京为已链接 formal；珠海未链接行可由明确登记日期作 provenance 分类，不能等同实际任务有效性。 |
| `formal_session_index` | 按同一自然人的实际正式采集顺序。第 4 次及以上保留；每人前三场只用于敏感性。 |
| `collection_reason` | 不足证据时为 `unknown_unlinked_registration`，不从模态缺失推断重采原因。 |
| `*_usable` | 模态级标志。单一模态缺失不得整场排除。 |
| `include_in_shared_primary` | 要求实际正式任务、probe 与时间线的确定性链接；不是登记/预约或程序历史推断。 |

跨站点模型仅在北京、珠海均有确定性 linked actual probe sessions 后运行。其最小模型为 `label1_binary ~ shared_protocol_progress + block + site + shared_protocol_progress:site`，以 `repeat_participant_id` 做 participant-level clustering，并报告 effect size（OR 或 beta）、95% CI 和 p 值。任何不足以估计的预定义问题必须保留 `NOT_ESTIMABLE`，而不是以北京单站点估计替代。
