# 厚粲杯项目工作区总账

更新时间：2026-08-25
维护角色：Codex 负责本地事实与路径更新；GPT 负责科研状态、优先级与解释边界更新。

> 这是 GPT、Codex 和用户共同使用的**唯一项目总账**。以后开始任何新任务前，必须先读本文件；任务结束后，必须更新本文件。禁止只在聊天或某一份 handoff 里记录“做过什么”。

---

## 1. 先说清楚：worktree 是什么

**worktree（工作树/工作区）就是你电脑本地真正放着代码、能运行脚本、能看到未提交修改的那个文件夹。它是本地的，不是 GitHub 网页。**

可以把三者理解成：

- **本地 worktree**：你电脑上正在工作的文件夹；Codex 能直接读写、运行代码、访问本地数据。
- **Git 分支**：这份代码当前属于哪条版本线，例如 `codex/gpt-codex-handoff-20260825`。
- **GitHub**：远程同步和交接层；GPT 能稳定读取这里，但 GPT **不能直接读取你电脑 D 盘里未上传的文件**。

因此，GPT 与 Codex 的高效协作必须依靠：

`本地 worktree / 本地产物 → Codex 记录到本总账 → GitHub → GPT 读取并裁决 → Codex 继续执行`

### 当前需要 Codex 补齐的本地工作区信息

以下信息在下一次 Codex 运行开始时必须补齐，不允许继续留空：

- mmwave-hrv-analysis 实际本地 worktree 根目录：`[待 Codex 填写]`
- 当前 worktree 对应分支：`codex/gpt-codex-handoff-20260825`
- FocusWave 实际本地 worktree 根目录：`[待 Codex 填写]`
- 厚粲杯数据根目录：`D:\Project\厚粲杯\11_数据\`
- 派生结果统一目录：`D:\Project\厚粲杯\11_数据\derived\`

以后若有多个 worktree，必须逐个记录：`本地路径 → 仓库 → 分支 → 当前 commit → 用途`。

---

## 2. 当前项目到底在做什么

项目目标不是“不断做审计”，而是最终回答三个问题：

1. 实验过程中，人的完全任务聚焦状态如何随时间、阶段和休息变化？
2. 行为、毫米波、近红外分别能提供什么信息，毫米波能否在时间和行为之外增加预测价值？
3. 若要把毫米波解释为心率变异性等生理指标，其数据链和逐搏算法是否经过足够验证？

当前最高优先级：**尽快产出北京正式纵向/事件相关结果，不再新增无必要审计。**

---

## 3. 已经完成且必须优先复用的核心资产

下面这些不是“参考”，而是**已有成果**。后续任务如果需要同类信息，必须先复用，禁止从零重做。

### A. C2 毫米波/行为基线与身份链

状态：`已完成，可复用`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\c2_radar_only_attention_baseline_v1\`

已知事实：
- 71 个 recording sessions；
- 1,317 个 probe；
- 46 个已恢复 `repeat_participant_id`；
- 已用于 participant-disjoint 分组分析。

**最重要的可复用资产：**
- `71 session → 46 repeat_participant_id` 的实际本地 crosswalk / manifest。

当前缺口：GitHub 只记录了“这张表存在”，还没有记录它的**准确本地文件名**。

下一次 Codex 必须首先在本目录找到这张表，并在本总账补充：
- 文件名；
- 完整路径；
- 关键字段；
- 行数；
- 生成它的 RUN_ID / 脚本。

**禁止再次重新恢复北京 participant identity，除非该资产确实不存在或无法与北京 session 对接。**

### B. C2 标签/时间结构审计

状态：`已完成，可直接引用`

已知事实：
- 当前 probe 四类含义已经在 FocusWave 程序资产中确认；
- label 1 = 完全专注于分拣任务；
- label 2 = 关注实验本身，但未聚焦分拣任务；
- label 3 = 实验无关思维；
- label 4 = 思维空白；
- time/block 结构本身具有明显预测信息。

注意：当前仍需确认**北京历史 BB 两阶段数据是否属于同一个固定 probe-response 程序家族**。这是一项“程序家族绑定”，不是逐 session 重新解释 1/2/3/4。

### C. 严格共同样本多模态基线

状态：`已完成，可写入当前结果`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\common_subset_baseline_v1\`

核心文件：
- `report.md`
- `common_subset_manifest.csv`
- `model_comparison.csv`
- `paired_bootstrap.csv`
- `participant_session_key_audit.csv`
- `run_manifest.json`

当前结论：
- 主集合 213 probe / 12 参与者 / 14 sessions；
- 时间/区组基线高于当前 radar-only、NIR-only 与简单融合模型；
- 这是“严格共同样本最小基线”，不是最终多模态上限。

### D. 完整实验结构分析设计

状态：`设计已完成，不需重做`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\longitudinal_event_analysis_v2_design\`

核心文件：
- `design_report.md`
- `analysis_question_variable_map.csv`
- `timeline_stage_schema.csv`
- `window_specification.csv`
- `missingness_QC_plan.csv`

已冻结：
- 北京两阶段；
- 珠海三阶段；
- probe 前 10/20/30 秒行为窗口；
- 休息/恢复分析；
- participant/session 重复测量结构；
- 不根据结果临时改窗口。

### E. NIR 方向性审计

状态：`已完成，不再重复查正负类`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\nir_directionality_audit_v1\`

已知事实：
- NIR-only AUC 低于 .50 不是 label 翻转，也不是 `predict_proba` 取错列；
- 不允许用 `1 - AUC` 改写成绩；
- 后续应转向参与者内轨迹、阶段/时间和 tonic/phasic 分解。

### F. 问卷测量审计

状态：`描述性审计完成`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\questionnaire_measurement_audit_v1\`

已知事实：
- 暂未确认可核验的正式多题量表；
- 单题可作为 trait-like 或 state-like 外部指标；
- 不计算无依据的 Cronbach’s α / McDonald’s ω。

### G. 静息/休息覆盖与 RS6240 质量审计

状态：`描述性审计完成`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\rest_break_coverage_qc_manifest_v1\`

注意：这里只是质量控制，不是 HR/BR/HRV 准确性验证。

### H. 北京现有时间线预检

状态：`结构已基本检查，不应重复扫`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\beijing_semantic_session_gate_event_v1\`

已知事实：
- 72 个候选 session；
- 71 个有有效 B1/休息/B2、trial/probe 时间结构；
- `sub-099_` 缺 `master_timeline.csv`；
- `sub-064_`、`sub-084_` 有 `experiment_abort`。

下一步不是重新检查这些结构，而是把 **A 项已有 C2 身份表直接 join 到这 71 个北京 session**。

### I. 珠海 session 链接预检

状态：`尚未恢复实际 session 映射`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\zhuhai_session_linkage_nir_event_readiness_v1\`

当前结论：
- 30 个登记 session；
- 实际采集 session 的确定连接目前为 0/30。

优先级：低于北京正式结果。

### J. RS6240 数据链技术门控

状态：`部分通过，生理解释仍阻塞`

本地目录：
`D:\Project\厚粲杯\11_数据\derived\rs6240_data_chain_technical_gate_v1\`

已知事实：
- 18/18 小分片支持 244–248 与 8–13 的 256 点镜像索引关系；
- `device_ms` 比 `host_ms` 更适合连续采样时间；
- firmware、Tx timing、memory mapping、calibration 仍未完整闭合。

禁止重复把 range-bin 镜像当作全新疑点重新调查。

---

## 4. 当前真正未完成的核心结果

这部分才是后续应该投入时间的地方。

### 北京正式纵向/事件相关结果

状态：`未完成，最高优先级`

需要产出：
- 完全任务聚焦比例随 time-on-task 的变化；
- B1 vs B2；
- probe 前 10/20/30 秒 reaction time、error、reaction-time variability；
- B1 末端 → 休息 → B2 起始恢复；
- participant/session 重复测量模型；
- 报告级图。

**最小剩余动作：**
1. 找到并复用 C2 的 `71 sessions → 46 repeat_participant_id` 本地实际文件；
2. 将它与北京 71 个有效 behavior/timeline sessions 做 deterministic join；
3. 一次性确认北京 BB 两阶段程序家族的 probe 1/2/3/4 语义；
4. 立即运行正式分析。

除非这四步暴露新证据，否则**不再增加新的北京 audit/gate**。

### 珠海三阶段正式结果

状态：`未完成，次级`

先恢复登记表 → 实际采集 session 的确定映射。北京结果未产出前，不扩大珠海模型任务。

### RS6240 HRV 正式验证

状态：`未完成 / blocked`

仍需要：
- firmware / Tx / memory/parser provenance；
- device time → 实验绝对时间锚定；
- 外部 Radar–ECG 正式逐搏 benchmark 数据。

当前不作为阻塞北京心理/行为分析的理由。

---

## 5. 防止重复劳动的硬规则

### 规则 1：Reuse First（先复用，后新建）

每个 Codex 任务开始前，必须先回答三句话：

1. 这个问题之前是否做过？
2. 本总账里有没有可以直接复用的本地文件？
3. 本次是在“复用/连接”还是“重新计算”？为什么？

如果本总账已有同类资产，默认必须复用。若要重做，必须在 handoff 中解释旧资产为什么不能用。

### 规则 2：本地关键文件必须记录“完整路径 + 文件名”

以后不允许只写：
`D:\...\derived\某目录\`

关键资产必须写到具体文件，例如：
`D:\...\derived\xxx\participant_session_crosswalk.csv`

并记录：用途、关键字段、行数、生成 RUN_ID、是否可复用。

### 规则 3：一个结论只允许有一个“当前权威资产”

如果新文件替代旧文件，必须在本总账写：
- `CURRENT`：当前使用哪个；
- `SUPERSEDED`：哪个旧文件已被替代；
- 替代原因。

不得让 GPT/Codex 在多个类似 CSV 中自行猜哪个最新。

### 规则 4：最多三条活跃主线

同时 active 的工作不超过 3 条。每条只写：
- 目标；
- 已有输入；
- 本次输出；
- 当前状态；
- 下一步。

没有明确输出的“继续调查”不能成为主线。

### 规则 5：GPT 不再凭摘要新增大 Gate

GPT 在提出新的 blocker / gate 前，必须先检查：
- 本总账；
- 现有 handoff；
- 旧资产是否已经解决该问题。

如果只是“旧资产没有被新任务读到”，应优先要求复用，不得重新立项。

### 规则 6：Codex 不得因 GitHub 没有被试级文件就假设“本地不存在”

GitHub 禁止上传被试级数据是隐私边界，不等于本地没有结果。

新任务必须先在本总账记录的本地目录中查找旧产物，再决定是否缺失。

### 规则 7：用户可读语言优先

面向用户的状态更新优先用中文普通话描述。

例如：
- `crosswalk` → “被试/session 对照表”；
- `semantic gate` → “标签含义与程序版本确认”；
- `participant-disjoint` → “同一个人不能同时出现在训练集和测试集”；
- `provenance` → “这个文件/结果是从哪里来的，可否追溯”。

首次确实需要专业术语时，再在括号中给英文。

---

## 6. 当前三条活跃主线

### 主线 1：北京正式结果【最高优先级】

目标：尽快产生第一批可写入论文/比赛报告的正式心理学结果。

已有输入：
- C2 的 71-session / 46-participant 身份资产；
- 北京 71 个有效时间线 session；
- 已冻结的 10/20/30 秒窗口与两阶段分析设计。

本次输出：
- C2 身份表与北京行为 session 的 join；
- 北京 BB 程序家族 probe 映射确认；
- 通过后立即运行正式纵向/事件相关分析。

禁止：再次从零恢复身份、再次重复检查 71 个 session 的时间结构。

### 主线 2：珠海实际 session 映射【后台次级】

目标：找到登记表到真实采集目录/session 的一对一关系。

本次只做链接，不跑 NIR/毫米波模型。

### 主线 3：RS6240 生理数据链补证【后台次级】

目标：补 firmware、Tx timing、memory/parser、绝对时间锚点。

不阻塞北京行为/心理结果；不调 HRV 算法。

---

## 7. 每次 Codex 结束时必须更新的最小格式

每个任务结束后，Codex 必须更新本文件对应条目，至少补充：

- `做了什么`：一句话；
- `复用了什么旧文件`：完整本地路径；
- `新产出什么文件`：完整本地路径；
- `结果是什么`：3–5 行；
- `是否替代旧文件`；
- `下一步`：只写一个最直接动作；
- `Git commit`。

如果任务没有产生新结果，只产生“又确认了一遍”，必须明确写：`NO_NEW_SCIENTIFIC_OUTPUT`，并解释为什么这个检查仍有必要。

---

## 8. GPT 每次读取时的固定顺序

GPT 后续不再从大量 handoff 猜项目状态，固定顺序：

1. 先读 `docs/WORKSPACE_LEDGER.md`；
2. 只读其中当前活跃主线明确引用的 handoff / 方法文件；
3. 若需要本地明细，要求 Codex从总账中的**具体文件**提取聚合事实，而不是重新跑；
4. GPT 的新裁决必须同步更新“当前三条活跃主线”和“真正未完成的核心结果”。

---

## 9. 用户如何判断“今天到底有没有进展”

以后每天不看 commit 数，不看审计文件数，只看三类产出：

1. **新科研结果**：新图、新统计结果、新模型比较、新生理验证；
2. **新可复用资产**：真正以后可以直接使用的身份表、时间线、共同样本表、数据映射；
3. **清除关键 blocker**：原来不能分析，现在可以分析。

如果一天主要增加的是 Markdown、handoff、PASS/BLOCKED 表，而没有上述三类之一，就不能称为实质性进展。

---

## 10. 2026-08-25 总账补全：实际 worktree 与 C2 身份资产

### 10.1 实际本地 worktree

| 仓库 | 本地路径 | 当前分支 | 当前 commit | 用途 |
|---|---|---|---|---|
| `greenboo26/mmwave-hrv-analysis` | `D:\Project\厚粲杯\08_算法\` | `codex/audit-j-target-lock-gate` | `5da545e1789fc16a0841786dff20846f98f5dcad` | 本地算法主工作区，存在用户既有未提交改动；本轮未修改 |
| `FocusWave` | `D:\Project\厚粲杯\05_实验\FocusWave\` | `formaltest` | `6f6dd0fc2ad3c10e43479cfd4e1ed5bd303604fa` | 北京 BB 两阶段程序与 Probe 资产来源 |
| GPT↔Codex handoff worktree | `D:\Project\厚粲杯\08_算法_worktrees\gpt-codex-handoff-20260825\` | `codex/gpt-codex-handoff-20260825` | 本次提交后更新 | 仅用于 GitHub 交接文件 |

厚粲杯数据根目录：`D:\Project\厚粲杯\11_数据\`
派生结果统一目录：`D:\Project\厚粲杯\11_数据\derived\`

### 10.2 C2 `71 sessions → 46 repeat_participant_id` 权威资产

**CURRENT（权威身份/被试-session 对照表）：**

`D:\Project\厚粲杯\11_数据\derived\analysis_tables_v2\subject_session_master_v2.csv`

- 文件行数：179 条数据行，65 个字段；包含多个站点和登记记录，不等同于 71 行 C2 结果表。
- 关键字段：`single_experiment_id`、`repeat_participant_id`、`repeat_count`、`site`、`session_date_time`、`j_source_folder`、`j_master_timeline_present`、`j_raw_behavior_present`、`j_raw_mmwave_present`、`m1_probe_windows`、`m1_probe_windows_ok`、`current_analysis_eligibility`。
- C2 实际运行使用该文件作为 `identity_master`，来源记录于：
  `D:\Project\厚粲杯\11_数据\derived\c2_radar_only_attention_baseline_v1\run_manifest.json`
- 生成/使用来源：`C2_RADAR_ONLY_ATTENTION_BASELINE_V1_20260825`；该 manifest 明确记录 71 recording sessions、46 restored `repeat_participant_id`，并采用 leave-one-repeat-participant-out 分组。
- 状态：`CURRENT / 可复用`，禁止重新恢复 participant identity。

**CURRENT（C2 模型审计结果，不是身份主表）：**

`D:\Project\厚粲杯\11_数据\derived\c2_evaluation_label_audit_v1\audit_predictions.csv`

- 用途：C2 标签和模型评估审计；关键字段为 `subject`、`probe_id`、`repeat_participant_id`、`label`、`target`、`fold`、`score`。
- 它不是 `71 sessions → 46 repeat_participant_id` 身份主表，不能单独用于 session identity 恢复。

**CURRENT（北京 71 个有效 behavior/timeline session 的确定性 join）：**

`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\deterministic_join.csv`

- 结果：70 个 `PASS_FORMAL`；C2 未匹配 `sub-099`（缺有效 `master_timeline.csv`）；北京 timeline 未匹配 `sub-067`（不在既有 C2 71-session crosswalk 中）。
- BB mapping：`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\bb_probe_mapping_once.csv`
- 运行清单：`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\run_manifest.json`
- 状态：`CURRENT / deterministic join 已完成；正式 longitudinal/event-related analysis 尚未运行`。

**SUPERSEDED / 不作为当前权威身份资产：**

- `D:\Project\厚粲杯\11_数据\derived\subject_modalities_v1\subject_session_questionnaire_master.csv`：问卷/模态登记主表，保留作来源记录，但不能替代 C2 实际 participant-disjoint 身份输入。
- `D:\Project\厚粲杯\11_数据\derived\beijing_longitudinal_event_v1\` 下的早期 preflight：仅记录旧 blocker；本轮以 `beijing_c2_identity_reuse_event_analysis_v2\deterministic_join.csv` 为北京 join 权威资产。

### 10.3 本轮动作与状态

- 做了什么：仅索引并登记实际 worktree、分支、commit、C2 身份输入和北京 deterministic join 产物；没有重新恢复身份、重新扫描原始数据或重算 C2 模型。
- 复用了什么：`subject_session_master_v2.csv`、C2 `run_manifest.json`、`deterministic_join.csv`、`bb_probe_mapping_once.csv`。
- 新产出：本节总账索引；随后已按冻结设计新增最薄行为分析启动脚本并运行北京正式行为纵向子集分析。
- 启动脚本（CURRENT）：`D:\Project\厚粲杯\08_算法_worktrees\gpt-codex-handoff-20260825\scripts\run_beijing_longitudinal_event_analysis_v1.py`
- 结果目录（CURRENT）：`D:\Project\厚粲杯\11_数据\derived\beijing_c2_identity_reuse_event_analysis_v2\formal_behavior_longitudinal_v1\`
- 具体结果文件：`report.md`、`model_results.csv`、`descriptives.csv`、`fig_error_trajectory.png`、`fig_preprobe_error_trajectory.png`、`trial_level_behavior.csv`、`probe_event_level_behavior.csv`、`run_manifest.json`。
- 结果摘要：70 个 PASS_FORMAL session、46 个重复参与者、59,080 个 trial、1,400 个 Probe；trial error 的 block 内进度效应 beta=0.251，95% CI [0.027, 0.474]，原始 p=.028；log RT 进度效应不明显；probe_response=1 概率随进度下降 beta=-0.893，95% CI [-1.501, -0.284]，原始 p=.004；B1/B2×进度交互未见明显证据。
- 当前状态：北京已从“无法开始”进入 `completed_behavior_only_formal_subset`；毫米波、NIR、ECG/RSP 未进入本轮模型。统计结果是首轮正式行为子集结果，仍需结合缺失模式、模型诊断和多重比较校正解释。
- 是否替代旧资产：不替代 C2 身份主表；仅明确 `subject_session_master_v2.csv` 为当前权威身份输入，明确 `audit_predictions.csv` 为模型审计结果而非身份表。
- 下一步：复核这批正式行为结果的模型诊断和报告图表，不重新恢复身份、不新增北京 gate；之后再决定是否把毫米波/NIR挂到同一已完成行为时间轴。
