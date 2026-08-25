# 北京—珠海正式实验协议与重复参与身份规则

状态：`BEIJING_ZHUHAI_SHARED_PROBE_PROTOCOL_CONFIRMED`

日期：2026-08-26

## 1. 正式实验协议关系

珠海正式实验自 2026-08-15 开始。FocusWave `formaltest` 分支中曾短暂出现 1–9 分即时专注评分的过渡版本，但该版本从未用于正式被试采集，因此不进入正式数据版本划分，也不作为后续分析中的 protocol stratum。

珠海正式实验采用 BBB 三个正式 Block；北京正式实验在 2026-08-18 将同一正式协议缩短为 BB 两个正式 Block。两地正式实验的核心注意状态探针、警觉度探针、B1/B2 任务序列和 probe schedule family 保持一致。因此：

- `shared_primary`：北京 B1+B2 + 珠海 B1+B2，可进入共同主分析；
- `zhuhai_extended`：珠海 B3，作为更长 time-on-task 的扩展分析；
- pooled 模型保留 `site`；
- participant/repeat participant 作为统计独立分组单位。

## 2. 珠海预实验与正式实验区分

珠海在正式实验开始前约收集了 10 名左右预实验被试。预实验使用 FocusWave 中明确标注的预实验程序分支，程序结构与正式实验存在较大差异。

后续身份表明确保留：

- `phase = pilot` / `formal`；
- `site = Zhuhai` / `Beijing`；
- `program_family` 或可追溯的 branch/version；
- `collection_reason`；
- `repeat_participant_id`。

珠海预实验数据作为独立 protocol family 保存，可用于 pilot-specific 分析、设备/流程质控或与后续正式实验做身份层面的纵向关联。正式 B1/B2/B3 probe-level 主分析使用 formal protocol 数据。

## 3. 正式重复参与与额外重采规则

北京和珠海的常规采集安排通常每名参与者最多安排 3 次正式实验。这个“3 次”是采集管理规则，主要用于避免同一参与者在同一天相同时间段连续重复实验，降低短时间练习、疲劳和状态延续的影响；它不是统计有效性的硬性上限。

同一自然人可以出现第 4 次或更多正式 session，尤其在毫米波、NIR 或其他模态发生质量问题后进行重采时。只要该次实验核心任务、probe 和时间线有效，就作为真实正式 session 保留。

canonical 数据层采用以下原则：

1. 每一次真实完成且核心实验结构有效的 formal session 都进入 person/session master；
2. `formal_session_index` 按真实正式采集顺序编号，可为 1、2、3、4 或更高；
3. `collection_reason` 记录 `routine`、`mmwave_retake`、`nir_retake`、`rgb_retake`、`multimodal_retake` 或其他明确原因；
4. 数据质量按模态判断，而不是按整场 session 一票决定；
5. 某一模态质量不足时，该 session 的其他有效模态、行为、probe 和问卷信息继续进入相应分析；
6. 只有核心实验结构本身无效，例如任务严重中断、关键 probe/timeline 无法恢复或无法确定正式协议身份时，才作为整场 formal-session exclusion；
7. 同一自然人的全部 session 在机器学习评估中始终进入同一个 participant group，保证 participant-disjoint；
8. 对重复 session 数量不均衡的影响，通过 participant-cluster 模型、participant-level bootstrap，以及必要时“全部有效 session vs 每人最多前三场”的敏感性分析评估，而不是预先删除第四场。

推荐 canonical 身份和 QC 字段：

- `person_id` / `repeat_participant_id`；
- `session_id`；
- `site`；
- `phase`：pilot/formal；
- `formal_session_index`；
- `collection_reason`；
- `retake_of_session_id`（若可确定）；
- `program_family`；
- `behavior_usable`；
- `probe_usable`；
- `mmwave_usable`；
- `nir_usable`；
- `rgb_usable`；
- `include_in_shared_primary`；
- `include_in_zhuhai_extended`。

## 4. 问卷中的“是否参加过第一阶段实验”题

珠海正式问卷比北京正式问卷多一个用于识别既往预实验参与经历的问题，核心用途是帮助区分“首次正式参与”与“此前参加过珠海预实验”。

北京问卷中只有前几个答卷因问卷尚未及时修改而保留了这一题；发现后立即删除。北京该题回答在后续分析中直接忽略，不作为北京问卷变量。

珠海该题定位为身份/provenance 辅助字段。它用于核对 pilot/formal linkage，不作为心理测量变量，也不进入专注状态预测特征。

## 5. 对后续分析的直接约束

1. 先建立北京—珠海统一 person/session crosswalk，并给每个 session 标注 site、phase、formal_session_index、collection_reason 和 program_family。
2. 对正式 session 建立模态级 QC，保留行为/probe/mmWave/NIR/RGB 各自可用状态。
3. `shared_primary` 使用北京 B1+B2 + 珠海 B1+B2 的全部核心结构有效正式 session；具体传感器模型再按对应模态 QC 形成 matched cohort。
4. 珠海 B3 作为 `zhuhai_extended` long time-on-task extension。
5. 同一人的全部 session 始终共享同一个 participant group。
6. 第 4 次及之后的正式 session 默认保留并记录原因；敏感性分析再评估重复次数不均衡是否改变结论。
7. 北京问卷中的“是否参加过第一阶段实验”残留字段直接忽略；珠海对应问题只用于身份桥接。

## 6. 解释边界

本裁决确认的是正式实验 protocol family、预实验区分方式和重复采集处理规则。当前统计原则是：保留每一次真实有效的正式实验，按模态决定能用什么，不按第几次决定整场是否保留。

具体哪些 session 属于 pilot、routine formal 或各类 retake，仍由 canonical crosswalk 使用预约、答卷、采集记录和模态 QC 逐场确定。
