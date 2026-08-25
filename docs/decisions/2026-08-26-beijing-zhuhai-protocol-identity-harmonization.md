# 北京—珠海正式实验协议与重复参与身份规则

状态：`BEIJING_ZHUHAI_SHARED_PROBE_PROTOCOL_CONFIRMED`

日期：2026-08-26

## 1. 正式实验协议关系

珠海正式实验自 2026-08-15 开始。FocusWave `formaltest` 分支中曾短暂出现 1–9 分即时专注评分的过渡版本，但该版本从未用于正式被试采集，因此不进入正式数据版本划分，也不作为后续分析中的 protocol stratum。

珠海正式实验采用 BBB 三个正式 Block；北京正式实验在 2026-08-18 将同一正式协议缩短为 BB 两个正式 Block。两地正式实验的核心注意状态探针、警觉度探针、B1/B2 任务序列和 probe schedule family 保持一致。因此：

- `shared_primary`：北京 B1+B2 + 珠海 B1+B2，可进入共同主分析；
- `zhuhai_extended`：珠海 B3，作为更长 time-on-task 的扩展分析；
- 后续 pooled 模型保留 `site`，不得假定站点效应为零；
- participant/repeat participant 仍是统计独立分组单位。

## 2. 珠海预实验与正式实验必须区分

珠海在正式实验开始前约收集了 10 名左右预实验被试。预实验使用 FocusWave 中明确标注的预实验程序分支，程序结构与正式实验存在较大差异。预实验不能仅因为 subject identity 相同而直接并入正式 B1/B2/B3 probe-level 主分析。

后续身份表必须明确保留：

- `phase = pilot` / `formal`；
- `site = Zhuhai` / `Beijing`；
- `program_family` 或可追溯的 branch/version；
- `is_retake`；
- `repeat_participant_id`。

如需要利用珠海预实验数据，只能另行定义 pilot-specific 分析或作为设备/流程质控资料，不得把其 trial/probe 标签与正式实验直接拼接成同一测量协议。

## 3. 两地重复参与规则

北京和珠海正式实验均允许同一参与者最多参加 3 次正式实验。`repeat_participant_id` 的定义必须以真实自然人为单位，而不是 session 数量。

如果同一自然人出现 4 个及以上 session，不能机械解释为“参加了 4 次正式实验”。必须逐 session 判定：

1. 是否有某次因为数据质量、设备故障或其他采集问题而进行重采；
2. 是否为珠海正式实验前参加过预实验，后续又参加正式实验；
3. 剩余 session 中有多少是真正有效的正式重复实验。

重采 session 与预实验 session 都必须保留 provenance，但不能计入“最多 3 次正式重复参与”的正式次数。

推荐 canonical 身份字段：

- `person_id` / `repeat_participant_id`：自然人身份；
- `session_id`：每一次实际采集；
- `site`；
- `phase`：pilot/formal；
- `formal_repeat_index`：仅正式有效 session 编号 1–3；
- `is_retake`；
- `retake_of_session_id`（若可确定）；
- `program_family`；
- `include_in_shared_primary`；
- `include_in_zhuhai_extended`。

## 4. 问卷中的“是否参加过第一阶段实验”题

珠海正式问卷比北京正式问卷多一个用于识别既往预实验参与经历的问题，核心用途是帮助区分“首次正式参与”与“此前参加过珠海预实验”。

北京问卷中只有前几个答卷因问卷尚未及时修改而保留了这一题；发现后立即删除。北京该题的回答不具有统一的测量条件，后续分析中直接忽略/剔除，不作为北京问卷变量，也不用于构念或效标分析。

珠海该题定位为身份/provenance 辅助字段，而不是心理测量变量。它可以用于核对 pilot/formal linkage，但不进入专注状态、问卷效度或预测模型特征。

## 5. 对后续分析的直接约束

1. 先建立北京—珠海统一 person/session crosswalk，再做 pooled 分析。
2. 珠海预实验必须与正式实验分层，禁止直接并入 shared-primary probe 数据。
3. 出现第 4 次或更多 session 时，必须先判定 pilot/retake/formal，而不是按 session 次数定义重复参与次数。
4. 北京问卷中的“是否参加过第一阶段实验”残留字段直接忽略。
5. 珠海对应问题仅作身份桥接和 provenance，不作心理变量。
6. 北京与珠海正式 B1/B2 可共同分析；珠海 B3 保留为 long time-on-task extension。

## 6. 解释边界

本裁决确认的是正式实验 protocol family 与身份处理规则，不代表珠海所有原始 session 已经完成确定性 person/session linkage。具体哪些 session 属于 pilot、retake、formal repeat 1–3，仍需由 canonical crosswalk 使用预约/答卷/采集记录进行逐场确定。
