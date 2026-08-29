# 本地独有真实分析收编表（2026-08-29）

状态：PARTIAL

本表使用已有只读审计 D:\Project\work\175项未提交内容审计_2026-08-29.md，不重新盘点 175 项，也不修改旧 dirty 工作树。

## 基线

- 旧仓库：D:\Project\厚粲杯\08_算法
- 旧分支/HEAD：codex/q1-questionnaire-criterion-validity-20260826 / 30c56ef2075a3abc3cca43fdd7557a6e8933d49b
- 目标：greenboo26/focuswave-multimodal-attention-analysis@main
- clean 目标工作树：D:\AI-Governance-Work\focuswave-central-mmwave-v2
- 收编前目标 HEAD：e7adab5cef87fb8d3d6b504816e0b914f6c2fbda
- 旧工作树状态：175 项（M 78 / D 57 / ?? 40）。
- 本轮未 reset、clean、force、切换旧 dirty 工作树、删除 clone/worktree、触碰 11_数据、运行中的 NIR 或重跑科学分析，也未创建分支。

## 收编计数（分析/证据包口径）

| 状态 | 数量 | 说明 |
|---|---:|---|
| LOCAL_UNIQUE_CURRENT | 9 | C1c、C1d、C2a、C2b task baseline、Issue #13 producer、#15 QC、B1/B2、merge readiness、RGB raw/context 报告 |
| 已进入 canonical main | 9 个分析包；本轮新增 117 个非缓存文件 | 含 66 个 legacy/历史脚本、6 个 mmWave pipeline、11 个 maintenance、23 个小型结果/报告、9 个透明性审计文件和 1 个收编表；无 raw/逐帧大型结果 |
| ALREADY_IN_MAIN | 多组 | M1、C1、C2B-v2、Q1 修正脚本、target-lock、behavior/probe 及已有审计目录已有等价入口/结果 |
| SUPERSEDED | 2 个结果包 | 旧 Q1 结果、旧 Issue #13 矩阵的 label 3/4 文案冲突 |
| PRODUCER_REPO_OWNED | 1 个仓库 | kyandi233-dev/Attention-Analysis；NIR/RGB runner/worktree 只登记 |
| HISTORICAL_ARCHIVE | 66 个文件 | 已置于 main 的 scripts/legacy，不计 active |
| UNRESOLVED | 18 个既有审计状态项 + 4 个 worktree/跨仓库资产 | 保留，待人工 adjudication |
| GENERATED_RESULT | 23 个小型结果/报告文件 | 大型结果只保留本地路径、manifest/hash |

## LOCAL_UNIQUE_CURRENT：分析→脚本→输入→输出→结果→决策

| 分析包 | 脚本/目标路径 | 输入与本地结果 | Git 报告/结论 |
|---|---|---|---|
| C1c mmHRV pilot | D:\Project\厚粲杯\08_算法\scripts\run_c1c_mmhrv_pilot.py → pipelines/mmwave/run_c1c_mmhrv_pilot.py | RS6240 raw ADC；结果 D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1 | docs/results/c1_pilot/C1C_PILOT_REPORT.md；可运行但无明显改善，不扩展、不称验证 HRV |
| C1d backend pilot | run_c1d_radarbeat_backend_pilot.py → pipelines/mmwave/run_c1d_radarbeat_backend_pilot.py | C1c 固定 waveform；同一 derived 目录 | C1D_PILOT_REPORT.md/c1d_decision.json；F1 平均下降，停止当前周期 HRV 开发 |
| C2a audit | audit_c2a_dataset.py → pipelines/mmwave/audit_c2a_dataset.py | 既有 C2a manifest/CSV | 只读 schema/coverage 审计，不改样本 |
| C2b task baseline | run_c2b_task_focus_baselines.py → pipelines/mmwave/run_c2b_task_focus_baselines.py | 既有 30 s feature matrix | 本地 c2b_task_focus_baselines_v1；supporting，不替代 canonical C2B-v2 |
| Issue #13 psychometric producer | build_psychometric_evidence_matrix_v1.py → scripts/build_psychometric_evidence_matrix_v1.py | Q1、behavior、repeat-session、LOSO aggregate CSV | 生成器已修正 label 3=走神、label 4=大脑空白；状态 PARTIAL，旧矩阵不收编 |
| #15 formal physiology/QC | maintenance/B2/build_formal/build_hr/run_hr 等 → scripts/maintenance/ | 既有 formal mmWave、ECG/RSP、QC、target-lock 表 | docs/results/mmwave_formal_vital_qc_v1/；HR/BR supporting/preliminary，HRV blocked |
| B1 corrected distance / B2 extreme range | rebuild_readiness_matrices_20260829.py、B2_extreme_range_target_audit_20260829.py、relabel_mmwave_readiness_flags_20260829.ps1 | 已有 corrected distance/session QC 表 | corrected 37 mm 改变 Tier 归类，不证明 vital-sign 可用 |
| #16/#17/merge readiness | build_merge_readiness_20260829.ps1、legacy/2026-08-27_issue17_formal_path/build_issue17_report_ready_matrix.py | behavior/probe、mmWave、NIR/RGB availability manifests | docs/results/final_merge_readiness_20260829/；70/46/1400 锚点，067 blocked、099 supplemental |
| RGB raw/context status | 中央只收报告，不收 RGB producer code | D:\Project\厚粲杯\11_数据\04_Attention-Analysis_nvidia-cuda_RGB | docs/results/rgb_current_status_v1/；71/72 raw/context ready，derived/iris/blink/PERCLOS 未完成 |

## ALREADY_IN_MAIN、SUPERSEDED、producer、temporary

- ALREADY_IN_MAIN：target-lock、M1、C2B-v2、Q1 修正 pipeline、behavior/probe baseline，以及已有 2026-08-24/29 审计结果目录均已在目标树存在；不重复复制。
- SUPERSEDED：旧 Q1 结果和旧 Issue #13 matrix 已确认 label 3/4 文案与冻结语义冲突；只保留修正后的生成器和 provenance。
- PRODUCER_REPO_OWNED：NIR fullclass、Issue #12 NIR ladder、NIR sensitivity、RGB worktree/source、clone3 mainline_c_v1 不跨仓库合并；producer remote 为 https://github.com/kyandi233-dev/Attention-Analysis.git。
- TEMPORARY：D:\Project\厚粲杯\08_算法\work\canonical_local_analysis_pipeline_v1、focuswave_repository_final_clean_clone_21b8bfc、focuswave_repository_final_clean_clone_3cd3433 仍是副本；不删除，待 clean/no-unique-result/sync 条件确认。
- UNRESOLVED：旧 dirty 工作树剩余 78 个 tracked modified 和 40 个 untracked status item 的用户/迁移/生成边界仍不能全部由文件名确定。

## 57 个 deletion 内容证明

对旧工作树 git diff --name-only --diff-filter=D 的 57 条逐项取 HEAD:path blob，与当前 scripts/legacy、scripts/maintenance/tools、scripts/maintenance/build_mmwave_audit.mjs 的 git hash-object 比较：

- exact migrated：57/57；
- unpaired：0；
- archive/历史版本 → scripts/legacy/2026-08_既有历史版本：完整匹配；
- scripts/tools/check_preexp_data.py、compare_all_datasets.py → scripts/maintenance/tools：完整匹配；
- scripts/审计/build_mmwave_audit.mjs → scripts/maintenance/build_mmwave_audit.mjs：完整匹配。
本轮未在旧 dirty 工作树提交 deletion；canonical main 新增完整迁移目标，原始工作保留。

## 当前有效分析 provenance

| 分析 | 状态 | 脚本 | 输入 | 输出/报告 | 结论 |
|---|---|---|---|---|---|
| HR | PARTIAL/supporting | scripts/maintenance/run_hr_course_99_corrected.py | formal mmWave + BIOPAC ECG/RSP | docs/results/mmwave_formal_vital_qc_v1/；本地 derived 路径见报告 | 既有 5 场/99 窗 HR course 误差 supporting；不是全队列 validated HR |
| BR | PARTIAL/preliminary | build_formal_vital_qc_v1.py、build_mmwave_algorithm_range_gate_audit_v1.py | QC、target-lock、RSP | mmwave_formal_vital_qc_v1/、BR 审计 | BR peak 误差 supporting；不作 validated BR |
| HRV C1 | VALIDATION_STOPPED | pipelines/mmwave/run_c1c_mmhrv_pilot.py、run_c1d_radarbeat_backend_pilot.py | RS6240 raw/waveform + ECG diagnostic reference | D:\Project\厚粲杯\11_数据\derived\c1c_mmhrv_pilot_v1 | C1c/C1d 未达门槛，停止当前周期开发 |
| formal physiology #15 | PARTIAL | scripts/maintenance/build_formal_vital_qc_v1.py + issue15 legacy | formal mmWave/ECG/RSP | docs/results/mmwave_formal_vital_qc_v1/ | 旧 17/53/2 与 corrected 33/37/2 都是 QC 归类，不是 vital use tier |
| task dynamics/#16 | PARTIAL | D:\Project\01_管理\04_分析脚本\analyze_J_Data_alertness_events.py（既有） | J_Data behavior/probe + existing event output | docs/results/2026-08-29_FORMAL毫米波任务动态警觉度_v1/ | 任务/警觉辅助证据；需沿用 #15 strata |
| denominator/#17 | PARTIAL/near ready | legacy issue17 + merge readiness | behavior/probe、mmWave、NIR/RGB manifests | docs/results/2026-08-29_Codex结果迁移_v1/、final_merge_readiness_20260829/ | 70/46/1400 锚点，067/099 边界明确 |
| target-lock | candidate-only | scripts/target_lock/combine_target_lock_gate.py、rgb_motion_gate.py | J distance/channel/time + RGB candidate | D:\Project\厚粲杯\11_数据\derived\j_mmwave_target_lock_audit_v1 | candidate，不称 chest lock confirmed |
| corrected B1 | QC rerun | scripts/maintenance/rebuild_readiness_matrices_20260829.py | corrected 37 mm tables | MMWAVE_FORMAL_VITAL_QC_V1_CORRECTED37MM.md | Tier 17→33 仅是 QC 变化 |
| extreme B2 | preliminary | scripts/maintenance/B2_extreme_range_target_audit_20260829.py | extreme-range QC tables | docs/results/2026-08-29_BR管线与极端距离审计_v1/ | 不升级生理结论 |
| QC | PARTIAL | build_formal_vital_qc_v1.py、build_mmwave_algorithm_range_gate_audit_v1.py | formal matrices/reference | docs/results/mmwave_formal_vital_qc_v1/ | A/B/C/D/E/U 分层，flag 不等于 pass |
| questionnaire | PARTIAL/REVISE_METHOD | pipelines/questionnaire/run_q1_questionnaire_criterion_validity.py、scripts/build_psychometric_evidence_matrix_v1.py | derived audit/bridge + behavior/probe aggregates | D:\Project\厚粲杯\11_数据\derived\questionnaire_criterion_validity_v1；Git producer only | criterion/convergent support，不是逐 Probe 或 trait reliability |
| behavior/probe | CANONICAL_BEIJING_REPORT_BASELINE | pipelines/behavior/run_final_report_cohort_baseline_v2.py | canonical behavior/probe | docs/results/final_report_cohort_baseline_v2/ | 70/46/1400 锚点 |
| C2B/C2C | C2B VALID_SUPPORTING；C2C PENDING_CANONICAL_RERUN | pipelines/mmwave/run_c2b_v2_canonical_reconstruction.py；run_c2c_personalized_mmwave_calibration.py | C2a/mmWave and within-subject derived | local derived paths in registry | C2B exploratory increment；C2C 不从旧结果推广 |
| NIR completed audit | ENGINEERING_ONLY/producer-owned | Attention-Analysis producer | D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR | canonical cards/provenance；Issue12 local-only | 69/72 engineering boundary，不进最终增量 |
| RGB pilot/engineering | ENGINEERING_ONLY/producer-owned | RGB producer | D:\Project\厚粲杯\11_数据\04_Attention-Analysis_nvidia-cuda_RGB | docs/results/rgb_current_status_v1/ | raw/context ready；derived/QC/inference 未完成 |
| multimodal LOSO | PLANNED_GLOBAL_ONLY | canonical fusion contract；旧 J evaluator 不直接复制 | matched behavior/mmWave/NIR/RGB inputs | docs/canonical/analysis_cards/multimodal_fusion.md | final result MISSING；本轮不运行、不猜 |

明确 MISSING：final multimodal LOSO、formal 70 场逐 session ECG/RSP vital pass、C1 full-cohort HRV、RGB derived-window feature；没有证据不填数值。

## work 副本

| 副本 | 事实 | 归属/处理 |
|---|---|---|
| canonical_local_analysis_pipeline_v1 | detached 53e3af5；0/28；issue12 local asset audit JSON | GENERATED_RESULT/TEMPORARY；不合并 |
| clone21 | main 21b8bfca；0/56；Issue12 NIR ladder 与 679 KB joined matrix/225 KB OOF | PRODUCER_REPO_OWNED；不合并 NIR |
| clone3 | main 3cd3433；0/55；frontend transparency audit、mainline C、Issue13 old output | 已合并 frontend audit 文本/CSV/脚本；PNG、NIR mainline C、旧 Issue13 matrix 不合并 |
| 01_Attention-Analysis_rgb-nvidia | rgb-nvidia 0307b1b；5 个未跟踪备份/状态脚本 | producer-owned，只登记 |

## 62 个 ahead commit 归属

| commit | 归属 |
|---|---|
| 30c56ef ALREADY_IN_MAIN；ba7a2c6 SUPERSEDED；d880d46 ALREADY_IN_MAIN；e20fcf8 ALREADY_IN_MAIN；dae3f42 ALREADY_IN_MAIN；6aacab3 SUPERSEDED；b2d713a SUPERSEDED；eafb335 SUPERSEDED |
| 6e7fe8f ALREADY_IN_MAIN；a54ddc5 ALREADY_IN_MAIN；5488430 SUPERSEDED/represented；9b4dc1b SUPERSEDED；af1a398 SUPERSEDED；681333e HISTORICAL_ARCHIVE；610d47a SUPERSEDED；4cb5c72 ALREADY_IN_MAIN |
| 439b211 HISTORICAL_ARCHIVE；ab707ac HISTORICAL_ARCHIVE；fc5d314 ALREADY_IN_MAIN；25ef25c ALREADY_IN_MAIN；e8933e7 SUPERSEDED；83b2e21 HISTORICAL_ARCHIVE；aaa12ef HISTORICAL_ARCHIVE/represented；7dee5f0 HISTORICAL_ARCHIVE |
| 4eec081 ALREADY_IN_MAIN；73b6468 PRODUCER_REPO_OWNED；bc4f651 ALREADY_IN_MAIN；0afac04 HISTORICAL_ARCHIVE；64c0926 ALREADY_IN_MAIN；1e42e02 HISTORICAL_ARCHIVE；6f6fe99 ALREADY_IN_MAIN；67b3e3b HISTORICAL_ARCHIVE |
| feb6cdf HISTORICAL_ARCHIVE；aa8e1a9 ALREADY_IN_MAIN；3ef6706 HISTORICAL_ARCHIVE；9f223e9 HISTORICAL_ARCHIVE；ffff90b HISTORICAL_ARCHIVE；e5b7c94 HISTORICAL_ARCHIVE；f5e852a ALREADY_IN_MAIN；961eb4a HISTORICAL_ARCHIVE |
| 745fdde HISTORICAL_ARCHIVE；c65538a HISTORICAL_ARCHIVE；baa8b6e HISTORICAL_ARCHIVE；fa846c1 HISTORICAL_ARCHIVE；22b61da HISTORICAL_ARCHIVE；19d49b1 HISTORICAL_ARCHIVE；61fe7cf HISTORICAL_ARCHIVE；26295d3 HISTORICAL_ARCHIVE |
| a51662c HISTORICAL_ARCHIVE；0cd6615 HISTORICAL_ARCHIVE；d89f798 HISTORICAL_ARCHIVE；3360e0a HISTORICAL_ARCHIVE；44e69a0 HISTORICAL_ARCHIVE；41d2b4e ALREADY_IN_MAIN；ccd21a4 ALREADY_IN_MAIN；ffb9c01 HISTORICAL_ARCHIVE |
| 5b6f29d ALREADY_IN_MAIN；4b9a919 ALREADY_IN_MAIN；e8d8ab1 HISTORICAL_ARCHIVE；994366b ALREADY_IN_MAIN；28f7718 ALREADY_IN_MAIN；e5deeb2 HISTORICAL_ARCHIVE |

没有 cherry-pick 62 个提交；每个 commit 的资产归宿已落到 canonical 等价入口、legacy、producer 或 superseded。

## 大型结果

未上传：C2B feature/OOF matrices、C1c waveform/诊断图、clone21 Issue12 joined/OOF、clone3 frontend PNG、canonical_local issue12 asset audit JSON。Git 只收小型报告、汇总、manifest、schema 和生成脚本；本地完整路径及哈希见对应报告/manifest和旧审计。

## 结论

已将可确认的中央 LOCAL_UNIQUE_CURRENT 收编到 clean canonical main；57/57 deletion 完整迁移；NIR/RGB producer 内容未跨仓库混入。旧 dirty 工作树仍不退休。

## unresolved closure（2026-08-29）

旧报告的 unresolved 计数是 Git status 折叠后的 22 个处理单元，不是 22
个文件。本表将每个处理单元归入最终允许状态；同一 worktree 内的混合
资产在“说明”列拆开记录。小文件已读取，大型矩阵/PNG/逐帧输出只核对
元数据、hash/manifest 和 ownership，没有运行分析。

| ID | 原路径/资产 | 类型；repo；branch/HEAD；dirty | 独有代码/结果；科学结论 | canonical/producer 检查 | 最终归类 | 后续动作 |
|---|---|---|---|---|---|---|
| U01 | `D:\Project\厚粲杯\08_算法\AI_PROJECT.md` | 导航；旧算法仓库；old branch/`30c56ef`；dirty | 无独有科学结论 | canonical main 有更新版 `AI_PROJECT.md` | SUPERSEDED | 保留旧副本，不覆盖/删除 |
| U02 | `NIR_FORMAL_DETACHED_RUN.ps1` | NIR launcher；Attention-Analysis producer；old branch/`30c56ef`；dirty | 只启动正式 NIR，不产 central 结论 | producer-owned | PRODUCER_REPO_OWNED | producer 侧维护；不迁入 central |
| U03 | `NIR_QUEUE_MONITOR.ps1` | NIR read-only monitor；Attention-Analysis producer；old branch/`30c56ef`；dirty | 只监视 batch/extension，不产科学结果 | producer-owned；最终快照未发现匹配运行 PID，仍按用户要求不触碰 | PRODUCER_REPO_OWNED | 保留原地 |
| U04 | `configs/vision_provenance.example.json` | 示例配置；旧算法仓库；old branch/`30c56ef`；dirty | placeholder，无实际输入/输出/结论 | central 有 `configs/paths.example.json`；无当前 producer 绑定 | HISTORICAL | 保留作旧示例 |
| U05 | `docs/WORKSPACE_LEDGER.md` | 工作区账本；旧算法仓库；old branch/`30c56ef`；dirty | 旧分支/C1 记录，结论已被 canonical status 覆盖 | canonical status/registry 已等价记录 | HISTORICAL | 仅作历史参考 |
| U06 | `docs/handoff/C1_C2A_HANDOFF_2026-08-26.md` | handoff；旧算法仓库；old branch/`30c56ef`；dirty | 阶段交接，无未收编 central 结论 | canonical decisions/status 已覆盖 | HISTORICAL | 不重复迁移 |
| U07 | `docs/results/2026-08-24_J_Data警觉度事件审计_v1` | 生成报告；旧算法仓库；old branch/`30c56ef`；dirty | #16 辅助结果，不是代码 | canonical result family/manifest 已登记 | GENERATED_ONLY | 保留 provenance；大结果不入 Git |
| U08 | `docs/results/2026-08-29_BR管线与极端距离审计_v1` | 生成报告；旧算法仓库；old branch/`30c56ef`；dirty | B2/range-gate supporting evidence | canonical QC/result index 已登记 | GENERATED_ONLY | 只保留小型报告 |
| U09 | `docs/results/2026-08-29_Codex结果迁移_v1` | 迁移报告；旧算法仓库；old branch/`30c56ef`；dirty | provenance，无新科学结论 | canonical assimilation report 已覆盖 | GENERATED_ONLY | 不重复处理 |
| U10 | `docs/results/2026-08-29_FORMAL_37mm*` | QC 生成结果；旧算法仓库；old branch/`30c56ef`；dirty | corrected-distance QC，不是 vital validation | canonical `mmwave_formal_vital_qc_v1` 已覆盖 | GENERATED_ONLY | 保留 report/manifest |
| U11 | `docs/results/2026-08-29_FORMAL毫米波任务动态警觉度_v1` | 生成结果；旧算法仓库；old branch/`30c56ef`；dirty | #16 辅助证据，不升级生理结论 | canonical result index 已登记 | GENERATED_ONLY | 不作为 active result |
| U12 | `docs/results/2026-08-29_HR峰值*` | 生成结果；旧算法仓库；old branch/`30c56ef`；dirty | HR supporting/QC，不是全队列验证 | canonical QC boundary 已登记 | GENERATED_ONLY | 不作为 validated HR |
| U13 | `docs/results/2026-08-29_RS6240*` | 生成结果；旧算法仓库；old branch/`30c56ef`；dirty | RS6240 exploratory/QC evidence | canonical result index 已登记 | GENERATED_ONLY | 完整输出留本地 |
| U14 | `scripts/audit_c1_alignment_robustness.py`、`repair_c1_alignment_protocol.py`、`replay_c1c_assets.py`、`run_c1c_mmhrv_pilot.py`、`run_c1d_radarbeat_backend_pilot.py` | 分析/审计脚本；central；old branch/`30c56ef`；dirty | C1 protocol/pilot；结论为 validation stopped | 等价入口已进入 `pipelines/mmwave/` | KEEP_IN_MAIN | 仅使用 canonical 路径 |
| U15 | `scripts/audit_c2a_dataset.py` | C2a audit；central；old branch/`30c56ef`；dirty | supporting audit，无 final claim | 已进入 `pipelines/mmwave/audit_c2a_dataset.py` | KEEP_IN_MAIN | 使用 canonical 入口 |
| U16 | `scripts/run_c2b_task_focus_baselines.py` | C2b supporting；central；old branch/`30c56ef`；dirty | exploratory task-focus baseline | 已进入 canonical pipeline | KEEP_IN_MAIN | 使用 canonical 入口 |
| U17 | `scripts/run_c2b_v2_canonical_reconstruction.py` | C2b reconstruction；central；old branch/`30c56ef`；dirty | canonical implementation，旧副本非唯一 | main 已有更严格实现 | KEEP_IN_MAIN | 不保留旧平行路径 |
| U18 | `scripts/legacy` | 历史代码；central；old branch/`30c56ef`；dirty | 历史实验/算法脚本，可能含旧结论；不计 active | 已完整迁入 `scripts/legacy/` | HISTORICAL | 只作 provenance，不运行 |
| U19 | `scripts/maintenance` | 维护脚本；central；old branch/`30c56ef`；dirty | QC/readiness/report helpers，无 final claim | 已进入 `scripts/maintenance/` | KEEP_IN_MAIN | 使用 canonical maintenance |
| U20 | `work/canonical_local_analysis_pipeline_v1` | 临时 worktree；central pipeline；detached/`53e3af5`；dirty 1 | Issue12 asset-audit JSON；无 central 新结论 | producer-side/local asset audit，不应复制到 central results | PRODUCER_REPO_OWNED | 保留原地，人工决定生命周期 |
| U21 | `work/focuswave_repository_final_clean_clone_21b8bfc` | clone；Attention-Analysis producer；main/`21b8bfca`；dirty 2 | NIR ladder、joined matrix、OOF；producer-side | producer-owned；大结果未进入 Git | PRODUCER_REPO_OWNED | producer 侧继续维护，不跨仓库合并 |
| U22 | `work/focuswave_repository_final_clean_clone_3cd3433` + `01_Attention-Analysis_rgb-nvidia` | clone/worktree；producer + frontend audit；main/`3cd3433`、`rgb-nvidia`/`0307b1b`；分别 dirty 5/5 untracked | frontend transparency 文本已收编；clone3 NIR mainline C 为 producer；旧 Issue13 matrix label 冲突；RGB 为 producer code | central 已收 frontend report；NIR/RGB producer-owned；旧 matrix superseded | PRODUCER_REPO_OWNED | 保留 dirty 副本；不得删除或跨仓库合并 |

### Closure counts

| final classification | count |
|---|---:|
| KEEP_IN_MAIN | 5 |
| PRODUCER_REPO_OWNED | 5 |
| SUPERSEDED | 1 |
| HISTORICAL | 4 |
| GENERATED_ONLY | 7 |
| SAFE_TO_REMOVE | 0 |
| BLOCKED_BY_RUNNING_TASK | 0 |
| remaining UNRESOLVED | 0 |

The old dirty branch remains protected because it still has `M 78 / D 57 /
?? 40`; closure means every known unresolved unit has a disposition, not that
the branch is safe to delete. No new central scientific conclusion was found,
and no result needs another upload or a new analysis run.
