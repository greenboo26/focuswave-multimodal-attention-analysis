# mmWave HR P2 failure attribution handoff

日期：2026-09-12
状态：`P1_COMPLETE / P2_AUTHORIZED / P2_NOT_EXECUTED`

## 1. 当前主线状态

当前 canonical main 在本 handoff 创建前为 `ca5521a8f4e8472e52da0d8387a38bbc622f6836`。P0、P1 与 180 s baseline audit 均已完成并有 durable record。

P1 在 exact `16729b2ef245f9304dae8674f3bac433bc02e98c`、冻结 B2 adapter/test/output identity、同一 5-session / 100-probe / 30 s / DLL host receive-enqueue time / pre-probe ECG denominator 上完成严格 paired A/B：control fused HR MAE=`10.4601 bpm`；恢复 P0 批准的 existing downstream bundle 后 fused HR MAE=`13.1737 bpm`，Δ=`+2.7136 bpm`；medianAE=`7.8590→11.7075`；bias=`−9.0160→−11.9765`；improve/worsen/tie=`30/70/0`；五场 MAE 全部劣化；global signal-quality gate hit=`0/100`。因此 P1 verdict 为 `PASS / RESTORATION_NOT_SUPPORTED`。

此 verdict 的精确含义是：**该四模块 bundle 不支持在当前 DLL-time、30 s、per-probe dynamic-target 合同下直接进入正式 producer。它不是对这些函数在所有 future target/window contracts 下的永久否定。** 如果 P2/P3 后续产生实质不同且已冻结的新上游 contract，需要重新受控验证，不得默认恢复，也不得默认永久排除。

HR/BR 当前继续 `HOLD / SUPPORTING_ONLY`；HRV 继续 `BLOCKED`；未授权注意状态模型使用该 HR 作为正式生理 predictor。

## 2. baseline audit 的当前解释

180 s baseline audit 是只读资产/方法审计，不是“最佳 baseline selector”验证，也没有实现最终 P3 selector。

冻结 cohort 为 116 sessions / 2320 probes；109/116 场有可分析 baseline。审计把推定 180 s 静息段切为 6×30 s，仅为了观察**当前正式 dynamic selector**在静息条件下的行为。六窗 exact HR bin+channel pair persistence median=`.167`、unique pair median=`6`，说明当前 selector 在 baseline 内本身不形成稳定单点 anchor。因此不支持“取 baseline 众数 bin/channel 后整场硬固定”这一简单方案。

历史 fixed-target 与旧 `run_c2c_personalized_mmwave_calibration.py` 仍是可复用方法资产，但不能直接当作 P3 final selector：前者绑定 historical first-6000/gate/60 s lineage，后者主要是 feature-level median/MAD 个体化且使用旧 Python timestamp，并未闭合 HR target anchor。

P3 仍未授权执行；其最终设计必须在 P2 结果之后决定。

## 3. P2 的唯一目标

P2 不是再试算法，也不是优化参数。P2 要在**当前 B2 control chain**上解释 `10.4601 bpm` 的剩余错误来源。

冻结 primary contract：

- 5 calibration sessions / 100 probes；
- exact B2 content identity 与 current control output；
- DLL host receive/enqueue timestamp；
- `[probe_end-30 s, probe_end)`；
- current per-probe dynamic target/bin/channel；
- current producer/adapter HR estimator；
- frozen ECG reference；
- 不加入 P1 restoration bundle；
- 不加入 baseline prior；
- 不改变 30 s window；
- 不训练模型。

P2 必须至少区分并量化：

1. selected target 上存在 ECG-consistent HR candidate，但 production 选错 peak/candidate；
2. ECG-consistent HR 信息主要存在于 nearby bin/channel，而 selected target 不优；
3. harmonic / half-frequency / double-frequency / mechanical locking；
4. heartbeat waveform 质量差或 candidate evidence weak/absent；
5. motion / phase / signal-quality 相关失败；
6. frame/timestamp/coverage/QC 问题；
7. 其它可复现类别；
8. 无法明确归因的 ambiguous cases。

旧 20 s truth-audit 比例（wrong-selection 102/325、nearby 182/325 等）只作历史线索，**不得复制成 current P2 结论**。P2 必须重新在 DLL-time 30 s、100-probe control 上计算当前比例。

## 4. ECG 使用边界

P2 是 retrospective failure attribution，因此 ECG 可以作为 oracle 评价“正确 HR 候选是否存在、位于何处、production 为什么错”。但 ECG 只能用于诊断，不得据此修改 producer、target policy、candidate threshold、quality gate 或正式参数。

如果需要定义“ECG-consistent candidate”容差、nearby bin/channel 邻域或错误类别优先级，必须先复用已有历史 truth-audit 定义；若现有定义与 current 30 s contract 不兼容，必须记录 `REUSE_REJECTION_REASON` 后再给出最小新定义，并将其标记为 diagnostic-only，不得以最小化本 100-probe MAE 的方式调参。

## 5. P2 输出与决策用途

P2 必须输出 100-probe machine-readable attribution table、session-level summary、category counts/percentages、按 absolute error 严重度的分层、典型 failure evidence、ambiguous denominator、manifest、脚本/commit/input/output/hash、以及 Issue #35 高可见同步。

尤其要单独报告 session `97795`，因为 current control MAE=`18.9463 bpm`，显著高于其它四场；但不得因它最差而改变分类阈值。

P2 完成后才决定下一步：

- 若主要是 target/bin/channel failure → P3 baseline-personalized target/soft prior 才获得方法学依据；
- 若主要是 candidate/peak/harmonic failure → 优先修 estimator/candidate selection，再决定是否进入 P3；
- 若主要是 signal quality/motion → 优先处理 waveform extraction/QC；
- 若 current 30 s 信息不足成为主要机制 → 才为后续 P5 30 s vs 60 s 提供依据。

P2 不授权直接实施这些修复；它只完成 failure attribution 并给出下一依赖。

## 6. 当前禁止事项

P2 期间禁止：

- 修改正式 HR producer；
- 恢复 P1 四模块 bundle；
- baseline-personalized selector；
- historical fixed-target promotion；
- 30/60 s final comparison；
- VMD/new clutter processing/new distance gate；
- beat/IBI/HRV promotion；
- attention labels 或注意状态模型；
- 依据 ECG 调整 production 参数。

## 7. 依赖与完成语义

P2 当前为 `AUTHORIZED / NOT_EXECUTED`。完成态应为 `PASS / FAILURE_ATTRIBUTION_COMPLETE`、`PARTIAL` 或 `BLOCKED`，并明确：当前主要 failure mechanism、证据强度、无法归因比例、是否支持进入 P3、以及下一步最小动作。

本 handoff 不替代 P0/P1/baseline audit 原始报告；其作用是把三者收束成 P2 的当前执行合同。
