# mmWave next execution prompt — 2026-08-30

Status: `ASSIGNED / TARGETED_VALIDATION_ONLY / #16 PAUSED`

Use this prompt verbatim for the next Codex/agent execution.

---

继续 `greenboo26/focuswave-multimodal-attention-analysis@main` 当前毫米波主线。

本轮不再做宽泛上游审计，也不重新讨论已经确认的固件身份、Range FFT、37 mm/bin、8-channel DataCube。正式采集全程使用 `mrs6240_p2512.img`，SHA-256=`7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`；缺少 machine burn/boot/version receipt 只作为 provenance limitation，不再作为“正式用了哪版固件”的 blocker。

先读取并服从：

1. `PROJECT_STATUS.md`
2. `docs/research/MMWAVE_PIPELINE_GAPS_AND_DECISIONS_2026-08-29.md`
3. `docs/research/MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`
4. `docs/research/MMWAVE_LITERATURE_EVIDENCE_AND_DECISION_LEDGER_2026-08-29.md`
5. `docs/research/MMWAVE_DEVICE_FIRMWARE_ENGINEERING_EVIDENCE_2026-08-30.csv`
6. `docs/canonical/MMWAVE_CURRENT_STATE_2026-08-29.md`

并只读参考最新总分析管线：

- `kyandi233-dev/Attention-Analysis@codex/formal-analysis-v2-portable`
- 重点：`configs/formal_multimodal_v2.yaml`
- 重点：`docs/060-formal-analysis/001-正式多模态V2路径与分析契约.md`
- 重点：`docs/060-formal-analysis/004-code-fix-ledger放行矩阵_20260829.md`

不要修改 `kyandi233-dev/Attention-Analysis@codex/formal-analysis-v2-portable`。它只用于确认下游 ingest/merge 契约；mmWave producer 权威仍在本仓库。

## 本轮唯一目标

关闭两个近端毫米波工程/科学问题，并据此判断能否冻结一版 merge-ready mmWave feature/QC contract：

1. target/bin/channel continuity；
2. respiration harmonic suppression 的正式策略与验证。

HRV 不在本轮救援范围，继续 `BLOCKED`。

---

## A. Target continuity：先补诊断，不重写算法

当前已知问题：现有结果只保存 segment-level 最终 selected bin/channel，没有跨窗口 previous/current history，因此无法判断相邻窗口是否稳定跟踪同一目标。

### A1. 只做最小 instrumentation

在现有正式 mmWave producer/runner 中加入最小只读诊断输出，不改变候选选择评分、阈值、窗口长度、距离门、HR/BR 算法和 QC 决策。

每个 analysis window/segment 至少记录：

- session / segment / window identifier
- HR selected bin
- HR selected channel
- BR selected bin
- BR selected channel
- previous HR bin/channel
- previous BR bin/channel
- bin displacement
- channel switch flag
- selected phase stability / phase variance（复用已有量）
- phase discontinuity/jump diagnostic（若现有相位链允许直接计算）
- HR/BR candidate score 或已有选中依据摘要
- existing QC outcome
- existing independent motion evidence / proxy（仅复用已有结果，不新开发 RGB）

instrumentation 必须默认不改变现有数值输出；若仅加诊断字段也会改变算法结果，立即停止并报告原因。

### A2. 先 representative，不跑 full formal batch

从已有正式数据中选少量代表性场次做 targeted rerun/diagnostic：

- 至少包含已知稳定候选；
- 至少包含历史 target-drift/phase instability 候选；
- 优先复用此前审计过的场次，避免扩大数据范围。

不得直接启动全样本 formal batch。

### A3. 必须回答

- HR bin hopping rate / channel switching rate；
- BR bin hopping rate / channel switching rate；
- phase instability 是否集中在 bin/channel switch 附近；
- 是否存在“无独立运动证据，但 target/bin/channel 切换并伴随 phase jump”的窗口；
- continuity 问题是否足以影响当前 HR/BR feature 的 merge-ready 资格；
- 若 continuity 已稳定，明确关闭该 blocker，不再扩展 target-lock 算法；
- 若不稳定，只给最小修复建议，不得直接开发新 target tracking、AoA、beamforming、VMD 或 multi-bin 路线。

---

## B. Respiration harmonic：做 A/B/C sensitivity，外部 RSP 不进入正式生产特征

当前已确认：标准 runner 没有传 `acq_path/ext_br_bpm`，所以现有 external RSP 2×/3× rejection branch 在标准正式运行中是 `INACTIVE`。

本轮决策原则：

- 不把 BIOPAC/RSP 作为最终 mmWave HR producer 的必需生产输入；
- 外部 RSP 只用于验证/诊断 respiration harmonic contamination；
- 正式可部署候选若需要 harmonic protection，应优先只依赖 radar 自己估计的 BR/内部信号；
- 不允许因为 `HR ≈ 2×BR` 或 `HR ≈ 3×BR` 就机械删除候选，必须避免真实 HR 恰好接近谐波位置时被误杀。

### B1. 固定三个版本

在同一代表性样本、同一窗口、同一 ECG 对照上比较：

A. `CURRENT`：当前正式 mmWave HR 链，不增加新 harmonic suppression；

B. `RADAR_INTERNAL_HARMONIC_GUARD`：只使用 mmWave 内部可得的 BR/候选信息做最小谐波保护；必须明确规则、容差、是否只降权还是拒绝、如何避免真实 HR 误删；

C. `EXTERNAL_RSP_DIAGNOSTIC`：允许用外部 RSP/BR 标记或排除 2×/3× respiration harmonic，但仅作为验证参考，不得升级为最终独立 mmWave producer 的必需输入。

### B2. 同窗比较输出

至少输出：

- session/window id
- ECG reference HR
- radar HR A/B/C
- radar BR
- external RSP BR（C only）
- A/B/C absolute error
- harmonic relation flag: near 2×BR / near 3×BR / neither
- candidate changed flag
- changed-from / changed-to frequency or BPM
- whether the change improved or worsened ECG agreement

### B3. 统计判断

至少比较：

- overall MAE
- harmonic-flagged subset MAE
- non-harmonic subset MAE
- improved / unchanged / worsened window counts
- catastrophic-error count（沿用现有项目定义；若无冻结定义，不得新造阈值，只报告分位/极值）

只有 B 在 participant/session matched 的代表性验证中显示稳定收益、且没有明显增加 non-harmonic 窗口误杀，才可提议升级到正式 producer。

C 无论结果多好，都只作为 external validation/diagnostic，不得成为最终 mmWave 独立贡献模型的隐藏输入。

---

## C. HRV 边界

HRV 保持 `BLOCKED`。

本轮不做：

- 新 HRV 算法；
- radar beat reconstruction 开发；
- ECG R-peak matching 开发；
- RMSSD/SDNN 的正式升级。

只保留既有结论：最早 blocker 是 radar beat ↔ ECG R-peak 同步逐搏匹配及 paired IBI agreement 缺失。

---

## D. merge-ready mmWave contract 决策

完成 A/B 后，明确列出一张 `ALLOW / HOLD / EXCLUDE` 表：

- 哪些 mmWave feature/QC 现在允许进入 `Attention-Analysis@codex/formal-analysis-v2-portable`；
- 哪些只允许作为 sensitivity/supporting；
- 哪些必须排除。

至少覆盖：

- HR
- BR/RR
- HRV/IBI
- target/bin/channel continuity QC
- phase stability QC
- motion/QC proxy
- missing/loadability status

不得把 external ECG/RSP reference 值本身作为最终 mmWave feature 输入。

下游必须遵守 portable V2 的原则：missing ≠ 0 ≠ success，participant/session identity 不得混淆，正式融合只 ingest merge-ready standardized table。

---

## E. 执行边界

允许：

- 修改本仓库 mmWave producer/runner，限于 A 的 instrumentation 与 B 的 targeted A/B/C validation support；
- 运行少量 representative targeted validation；
- 生成新 diagnostic CSV/JSON/manifest/report；
- 更新 canonical GitHub 文档与必要测试。

禁止：

- 不运行 Issue #16；
- 不重跑 C2B/C2C；
- 不启动全样本 formal batch；
- 不开发新 target-lock 路线、AoA、beamforming、VMD、multi-bin search；
- 不修改原始数据；
- 不修改 NIR/RGB producer；
- 不修改 `kyandi233-dev/Attention-Analysis@codex/formal-analysis-v2-portable`；
- 不把 external RSP 变成最终正式 mmWave producer 的必需输入；
- 不把 phase/QC failure 自动解释为 participant movement；
- 不把 HRV 升级为可用特征。

---

## F. 验证与提交

代码修改后必须：

- 跑相关单元测试；
- 做 syntax/import 检查；
- 验证 instrumentation 不改变 CURRENT 数值结果；
- 保存代表性运行 manifest、输入范围、代码 commit、配置 digest、输出 hash/provenance；
- 不上传原始数据或大型逐帧/波形资产。

同轮更新现有 canonical 文档，不新建平行治理系统：

- `PROJECT_STATUS.md`
- `docs/research/MMWAVE_FORMAL_PIPELINE_LINE_BY_LINE_AUDIT_2026-08-29.md`（若调用链/输出合同变化）
- `docs/research/MMWAVE_PIPELINE_GAPS_AND_DECISIONS_2026-08-29.md`
- `docs/research/MMWAVE_LITERATURE_EVIDENCE_AND_DECISION_LEDGER_2026-08-29.md`（绑定本轮文献决策）
- `docs/canonical/MMWAVE_CURRENT_STATE_2026-08-29.md`
- `docs/canonical/RESULT_INDEX_V1.md`（若产生新正式/验证结果）
- `CHANGELOG.md`（若有 material code/scientific decision change）

最终直接提交并 push `main`；不要新建分支。

---

## 完成状态

只有 A 和 B 均完成 targeted validation、并给出 merge-ready feature/QC 决策后才报：

`PASS / MMWAVE_MERGE_READY_CONTRACT_FROZEN`

若代码/诊断完成但证据不足：

`PARTIAL / MMWAVE_TARGETED_VALIDATION_INCOMPLETE`

若发现现有实现无法在不改变主算法的前提下完成验证：

`BLOCKED / NEEDS_EXPLICIT_METHOD_CHANGE_AUTHORIZATION`

始终保持：

`HRV = BLOCKED`
`ISSUE_16 = PAUSED`
