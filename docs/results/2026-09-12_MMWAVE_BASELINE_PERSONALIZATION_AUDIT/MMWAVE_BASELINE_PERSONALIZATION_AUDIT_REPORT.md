# FocusWave 正式实验 180 s 静息基线资产与方法审计

## 1. 状态与范围

本轮完成的是 P3 baseline-personalized heart-rate calibration（基线个体化心率校准）之前的只读资产与方法审计。审计没有修改正式 heart rate（心率 [HR]）producer，没有实现最终 baseline selector（基线选择器），没有用 electrocardiography（心电图 [ECG]）结果调 target/bin/channel，没有训练注意状态模型，也没有在 30 s 与 60 s 之间作最终选择。

审计状态为 `AUDIT_COMPLETE / P3_EXECUTION_NOT_READY`。审计期间 canonical `main` 已由 commit `5bbb2de0b715d02d4c5de5de889c5ac8ec30e3b7` 完成 P0 lineage 收口；方法候选已经可以被清楚定义，但 P3 仍须等待 P1 受控工程回归，以及本报告第 9 节的预注册与时间语义条件。因此 `P3_DESIGN_READY=NO`；这里的 NO 指不能开始正式比较或 producer 变更，不是否定已有基线资产。

## 2. 采集事实与时间语义

正式实验 acquisition（采集）仓库 `kyandi233-dev/FocusWave@formaltest` 的 `01-MainProgram/main_experiment_msmf.py` 在 near-infrared（近红外 [NIR]）、red-green-blue video（可见光视频 [RGB]）和 millimeter wave（毫米波 [mmWave]）均已启动且持续采集后写入 `baseline_start`，调用 `show_resting_baseline()`，返回后写入带 `duration=...s` 的 `baseline_stop`。`core/sart_task.py` 将默认静息时长固定为 180 s；流程为先显示坐姿确认页并等待空格，再呈现纯色静息画面 180 s，期间不采集行为按键，倒计时结束自动继续。

关键限制是：`baseline_start` 在等待坐姿确认之前写入，不是静息画面 onset（开始时点）。冻结 116 场中 115 场有唯一 start/stop 标记，标记包络为 180.944–245.788 s，*Mdn* = 182.751 s；超出日志 180 s 的部分中位数为 2.751 s，最大为 65.788 s。日志记录的静息时长在 115 场均为 180.0 s。因此：

- `baseline_start → baseline_stop` 是“坐姿确认等待 + 180 s 静息”的直接观测包络；
- 本轮用 `baseline_stop − logged duration` 得到的 180 s 仅为 `INFERRED_FROM_BASELINE_STOP_MINUS_ROUNDED_LOGGED_DURATION`，日志只保留 0.1 s 精度；
- 该推定 onset 可用于资产/QC 描述，不能伪装成直接记录的静息 onset，更不是雷达硬件 frame-start timestamp（帧开始时间戳）。

正式切片继续采用冻结的 DLL（dynamic-link library，动态链接库）host receive/enqueue time（主机接收/入队时间）CSV 第 2 列，即 zero-based column 1；Python worker 写入时间只允许作处理延迟质量控制。本轮没有回退到旧个体化脚本使用的 Python timestamp。

## 3. 冻结分母、可用性与质量控制

分母严格来自既有 `J72 + E44 = 116 sessions / 2320 probes` 冻结表，不从原始目录扩张。当前两表实际包含 62 个非空 `repeat_participant_id` 组；参与者级开发/验证拆分必须以这个字段为准，并在进入 P3 前再次冻结 identity manifest（身份清单）。

| 批次 | 冻结 session | 可分析 180 s 基线 | 结构性缺失 | 可用率 |
|---|---:|---:|---:|---:|
| J | 72 | 70 | 2 | 97.22% |
| E | 44 | 39 | 5 | 88.64% |
| 合计 | 116 | 109 | 7 | 93.97% |

7 场结构性缺失可完全分类：1 场缺 `master_timeline.csv`，2 场缺 mmWave timestamp CSV，4 场 timestamp CSV 为空。没有把这些 session 删除后重定义正式分母，也没有用邻近 session 或其他模态补值。

109 场可用基线全部通过 NPZ（NumPy compressed data cube，NumPy 压缩数据立方体）累计帧数与 timestamp 行数一致性检查，并产生 654/654 个 audit-only（仅审计）30 s 描述性切片。推定 180 s 窗的帧数为 17,786–17,922，*Mdn* = 17,819；相邻 DLL 时间中位数在 109 场均为 10 ms，95 百分位数为 11–13 ms；>50 ms、>100 ms 相邻间隔均为 0，frame-ID discontinuity（帧编号不连续）为 0。相对固定 100 Hz 的名义覆盖率中位数为 .9899；它是固定采样率索引密度诊断，不等于已证明传感器无丢帧。

## 4. 当前基线信号/特征处理图谱

本轮直接复用正式 DLL-time adapter 与 `process_vital_signs_v3_1_1.py`，处理链为：

`baseline_stop − logged duration` 推定 180 s → DLL host-time `[start, end)` 帧索引 → NPZ 多 channel 复数 range cube（距离维数据立方体）→ audit-only 六个连续 30 s 切片 → 当前 raw mean-power range profile（原始平均功率距离剖面）→ 每 channel 的 bin 候选 → phase stability（相位稳定性）与 HR/BR band signal-to-noise ratio（频带信噪比）评分 → 当前动态 HR/BR bin/channel → 相位展开位移 → 现有滤波、peak/course/fusion（峰值、时间进程与融合）链 → 仅描述性 HR/BR 与 QC 字段。`

当前 selector 的 HR 候选分数为 `log1p(HR SNR) × phase_stability²`；呼吸候选使用 `BR SNR × phase_stability`。本轮在不改变选择结果的前提下，额外从同一候选表导出：最佳分数、最佳与次佳的 margin（分数差）、selector SNR、相位稳定性、被选 bin/channel 平均功率、相对同 channel 中位功率的对比，以及六个切片间的 bin/channel/pair persistence（持续性）。这些是审计统计，不是新 selector。

producer 目前没有在正式输出中持久化 target power、selection margin 或 180 s persistence；`mmwave_target_switch_rate` 仍为空。selector 输入是 post-Range-FFT complex cube（距离快速傅里叶变换后的复数数据立方体）的 raw mean-power profile。本链没有 selector-integrated static/clutter removal（选择器内静态/杂波去除）；既有 display-only 减均值图不能当作运行中的 clutter suppression（杂波抑制）。

## 5. 目标稳定性与基线 HR/BR 描述

109 场中，六个 30 s 切片的 HR 精确 bin+channel pair（距离单元与通道组合）持续率中位数为 .167，四分位区间为 .167–.333；每场不同 pair 数中位数为 6，范围 3–6；modal pair（众数组合）最长连续运行中位数为 1 个切片，最大为 2。单独 bin 与 channel 持续率中位数均为 .333。该结果说明当前逐窗动态 selector 在静息基线内并不自然形成稳定个体锚点；不能直接把六窗众数升级成最终 baseline anchor（基线锚点）。

654 个切片的被选 HR bin 范围为 2–255，中位数为 11，但第 75 百分位数为 244；只有 309/654（47.25%）落在历史 bins 9–40 gate（门控）内，345/654 在其外。当前选择分数 margin 中位数为 0.0524，四分位区间 0.0180–0.1295；相位稳定性中位数为 .9581；这些量尚无冻结通过阈值。

现有 producer 给出的 fused HR（融合心率）中位数在切片层面为 76.7 bpm，四分位区间 69.2–83.8 bpm；breathing rate（呼吸率 [BR]）中位数为 18.084 breaths/min，四分位区间 14.070–20.148。654/654 个 HR 与 BR 值分别位于 producer 内部 48–120 bpm 和 6–30 breaths/min 搜索范围。这个 100% 是算法搜索/输出范围内的描述，不是 ECG 准确性、构念效度或正式生理结果；HR/BR 继续 `SUPPORTING_ONLY / HOLD`，heart-rate variability（心率变异性 [HRV]）继续 `BLOCKED`。

## 6. 既有可复用资产与缺口

可直接复用的资产：

1. acquisition 的 180 s 时长、持续三模态采集和 start/stop 日志机制；
2. 冻结 116-session/2320-probe cohort 表及当前 62 个非空 repeat-participant 组；
3. 109 场可读 baseline timeline、DLL timestamp 与 complex cube；
4. 当前完整动态 selector、相位/运动/功率候选信息与正式 downstream HR/BR 处理链；
5. 历史 fixed-target（固定目标）完整链及 60 s/5-session/99-valid 历史 reference；
6. 旧 `run_c2c_personalized_mmwave_calibration.py` 中的 baseline marker 解析、10/30/60 s 窗枚举、21 项 robust median/MAD（稳健中位数/绝对中位差）局部校准特征构造，可作为代码级参考。

旧 C2C 脚本不能原样成为 P3 selector：它只覆盖 J72，30/60 s 成功 70/72；用 Python timestamp 作主对齐；其 21 项 `W` 不含 `q_target_bin`、`q_target_channel`、`q_bin_stability_10s`，也不形成 baseline target anchor；脚本后半段训练注意状态 logistic regression（逻辑回归）并执行 grouped cross-validation（分组交叉验证），超出本轮与 P3 calibration-only 边界。canonical card 已将它标为 `SUPERSEDED_PENDING_CANONICAL_RERUN`。

当前缺口为：7 场结构性缺失；115 场均无直接静息 onset 事件；没有雷达硬件 frame-start timestamp；没有冻结的逐 session 物理 target/distance truth（目标/距离真值）；没有 canonical 的 baseline-aligned ECG reference（基线对齐心电参考）清单；没有预注册的 anchor 稳定性阈值、neighborhood（邻域）、prior weight（先验权重）、失败回退与 30/60 s 选择规则；没有冻结的 participant-disjoint 开发/验证 manifest；正式输出尚未持久化 power/margin/persistence。

## 7. 与历史 fixed-target 方案的关系

历史最佳 reference 绑定到 `run_hr_course_99_corrected.py → process_vital_signs_v3_1_1.py`：8-channel complex range cube、前 6000 frames 选择并固定 target、`0.037 m/bin`、`0.30–1.50 m = bins 9–40`、phase unwrap、segment correction/consensus/time-course；5 场、99 个有效 60 s 窗的历史 HR mean absolute error（平均绝对误差 [MAE]）为 3.7772146 bpm。

它与正式 180 s baseline anchor 有机制上的可复用关系——都用任务前数据估计 target 后在任务段保持或约束 target——但两者不等价。正式采集在设备启动后还有界面/看板与坐姿确认；“前 6000 frames”可能混合 baseline_start 之前、坐姿确认等待和部分静息内容，并未绑定当前 180 s 纯静息事件。历史 bins 9–40 是固定 gate，而当前正式动态 selector 在全部 256 个 bin 上搜索；即使正式 adapter 以 0.037 m/bin 保存距离 proxy（代理量），两者也不是同一 target contract。因此历史 fixed target 只保留为受控 comparator（比较臂）与方法来源，不可直接移植成正式 baseline selector，也不可用 3.777 bpm 倒推 116 场正式性能。

## 8. P3 最小候选设计与泄露防护

本轮只冻结候选设计空间，不冻结实现或最佳参数：

- Arm A：当前 DLL-time 30 s 动态 selector 与完整 downstream 链，原样 comparator；
- Arm B：历史 fixed-target 合同的受控、可追溯 comparator，明确它的 gate、距离与 first-6000 语义，不把它叫正式 baseline arm；
- Arm C：baseline-personalized soft-prior candidate（基线个体化软先验候选）。它只可读取同一 session 任务开始前的静息数据，形成 bin/channel 分布、持续性、power、margin、phase、motion 和 baseline HR/BR QC；任务窗仍运行同一候选生成与 downstream estimator，只允许用预注册的 baseline anchor/neighborhood 对候选排序或回退，不能强迫 task HR 接近 baseline HR。

30 s 与 60 s 都必须作为候选保留：30 s 可形成 6 个基线切片，60 s 可形成 3 个；选择规则、阈值、邻域和先验权重必须在开发参与者内冻结，再一次性评估保留参与者。当前 30 s 仅是与 formal pre-probe window 对齐的审计分区，不是本报告选出的最终时长。

泄露防护要求：

1. 以 `repeat_participant_id` 分组；同一人的所有 session 必须在同一 fold（折）内，不能只按 session 分割；
2. held-out participant（留出参与者）可以在推理时使用其本场任务前、无标签 baseline 作个体校准，但不得用其任务窗、注意标签、ECG 或后续 session 调超参数；
3. 30/60 s、阈值、邻域、权重、fallback（回退）和 feature scaling（特征缩放）只能在训练/开发 fold 内决定；
4. ECG 仅可作为冻结 validation reference（验证参考）计算 HR 误差，不能参与 target/bin/channel 或阈值选择；若用于开发调参，必须另留独立确认集；
5. 所有 Arm 使用相同 DLL-time、窗口端点、ECG eligibility（心电资格）、HR/BR estimator、缺失保留和分母；不得按结果删低质量窗；
6. 主比较须报告覆盖率、失败原因、participant-level 配对误差与不确定性，不能只报告 pooled probe MAE；多候选比较需预先定义 primary contrast（主要对比）和 multiplicity（多重比较）处理。

## 9. P3 启动前置条件与禁止项

P0 已完成；P3 启动前仍必须同时满足：P1 用同一输入证明恢复链没有工程回归；冻结 baseline onset 处理（新增直接 marker，或明确接受 stop-minus-rounded-duration 的误差合同）；冻结 116-session/62-group identity manifest；冻结 30/60 候选、anchor 稳定性、邻域、权重、回退和 missingness（缺失）规则；确定 baseline-aligned ECG 的实际可用分母及独立开发/确认拆分；保留 HR/BR `HOLD`、HRV `BLOCKED` 直到独立 admission gate（准入门）通过。

禁止：修改正式 HR producer；把六窗众数直接作为最终 selector；按 ECG MAE 逐 participant 选 target/bin/channel；用 task HR/标签反向调 baseline anchor；把结构性缺失删除后缩小正式分母；用 Python timestamp 替代 DLL time；把 bin×spacing 当实测胸部距离；把 baseline HR 当 task HR 的硬目标；训练注意模型；提前宣称 30 s 或 60 s 胜出；把本轮描述性 HR/BR 写成正式科学结果。

## 10. 可追溯执行记录

- canonical audit repo baseline：`greenboo26/focuswave-multimodal-attention-analysis@main`，审计起点 `b33e277620d43ca0e0a9960b5702dea7cf2dac87`；
- acquisition source：`kyandi233-dev/FocusWave@formaltest`，`a4f2a6ee4eda2b4de42be538abb1ecf550380ca1`；
- 正式 DLL-time producer/adapter source：`16729b2ef245f9304dae8674f3bac433bc02e98c`；producer SHA-256=`bc65c2d2c99ebdfedea2500579caeb45cb8918466cf788ade718806bdd351fda`，adapter SHA-256=`434f0c60234f6ae9c319e0f20f151cc1b0794b0be65645e8e5df372a0ae575e9`；
- frozen J table：1,440 rows / 72 sessions，SHA-256=`bc827dc317982ae0e920f661e28cec023473eccfcb034bc806e1a3583ef7828c`；
- frozen E table：880 rows / 44 sessions，SHA-256=`b7ea774ccebb6e35397a56e76f108a63d41803bf697260d01977effa5fad3e36`；
- 既有 C2C 脚本 commit=`11c0b61a8ba492ce44ca26b93a2d35db053af70d`，SHA-256=`ad3daa2ab5754b34f43e902e1ae97788e452c79f137ede6791c90d03b81277ae`；
- 本轮执行入口：`scripts/maintenance/audit_mmwave_baseline_personalization_20260912.py`；聚合入口：`scripts/maintenance/summarize_mmwave_baseline_personalization_audit_20260912.py`；
- local-only output：`D:\Project\厚粲杯\11_数据\_FormalAnalysis\mmWave\mmwave_baseline_personalization_audit_20260912\`；逐 session 116 rows、逐 30 s 切片 654 rows；
- 逐 session SHA-256=`c4887afe79a0654df8e99a1acd7dd898cdb14689f3b3521c30c08851e24bae1b`；逐切片 SHA-256=`b5cd41475326e97efae69312e7b02c0209572fe590cf4e13cf50bec074f46aa7`；
- Git-safe aggregate：`MMWAVE_BASELINE_AVAILABILITY_SUMMARY.csv`、`MMWAVE_BASELINE_AUDIT_SUMMARY.json`；逐 session/session ID 数据不提交。

完整命令、Python/NumPy 版本、输入 timeline/timestamp 哈希与所有输出哈希保存在 local-only `manifest.json`。`models_trained=false`、`formal_hr_producer_modified=false`、`final_baseline_selector_implemented=false`、`ecg_used=false`、`attention_labels_used=false`。
