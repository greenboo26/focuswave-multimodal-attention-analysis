# Issue #29 Supervisor evidence audit — Round 1

审查基线：canonical `main` 与本隔离 worktree 均核验为 `805db1d3f2d701d46f678b7cd911990f779a4966`；`origin/main` 与 `git ls-remote origin refs/heads/main` 同 hash。审查对象是 Issue #24–#28 的实际脚本、结果、manifest、治理同步和本地提交，不以会话文字作为科学证据。

## Round 1 decision

`REUSE_GATE=PASS`（整体）：#24–#28 的复用链、必要的 `REUSE_REJECTION_REASON` 和实际执行提交均已核验。#25 最终 manifest 已补齐 #24 lineage、283-pair 分母、脚本/输出 hash 和运行验证。

`SCIENTIFIC_GATE=PARTIAL`（整体）：没有任务获得正式 HR/BR validity promotion。#24 完成 ECG eligibility 层；#26 的距离–误差描述性审计通过但 physical gate unresolved；#27 仅 supporting retrospective oracle audit；#28 的历史 acquisition tail 不可恢复。HR 继续 `HOLD`，HRV 继续 `BLOCKED`。

## Item findings

### #24 — PASS / PARTIAL

本地提交 `d2d09f8ac502600d3a1241e33c429bd53756fa45`。实际分母为 335 个 DLL-time windows：`ECG_VALID=325`、`ECG_INVALID=10`、`UNRESOLVED=0`。invalid primary reason 与 57 个 marker warning 分离，没有把 warning 重复计入 invalid。ARM 指标仍是固定既有输出的描述性重分母，不改 estimator、target 或 formal validity。

接受条件已满足：复用 `gold_standard_qa.ecg_qa` 和 block marker affine mapping，manifest 有 run ID、输入 hash、规则和 local-only row-level 边界；未改 raw/producer/C2B/C2C。接受为 ECG reference layer，不接受为 HR validity。

### #25 — PASS / PARTIAL bounded diagnostic only

本地提交 `c4b5397971c98270520b1eec9ec81cda8592e9dd` 已闭合最终证据。303 个固定 pair endpoints 中，283 对 20 s 与 trailing 60 s 均通过 #24 同源 eligibility；20 s/60 s MAE 为 14.703129/5.608574 bpm，且明确 diagnostic-only、未按 MAE 选窗长。manifest 已记录 #24 lineage、283-pair 分母、脚本/输出 hash、canonical 基线、run exit 和 empty-metric guard。

接受边界：可按 bounded diagnostic evidence 整合，但不得提升为 formal window validity，也不得把旧的 0 分母结果解释为“无差异”。

### #26 — PASS / PARTIAL

本地提交 `6990364151d544d54b297ce394b4ff9e5f20c1d7`。复用 corrected `selected_bin × 0.037 m`，正式距离层为 71 sessions 的描述性分布；早期 reference 层严格保留 5 participants/99 windows。没有新增 physical threshold 或按 MAE 排除。distance–error 描述性审计通过，但人体真实摆位/物理成因缺失，physical gate 仍 `UNRESOLVED`。

### #27 — PASS / PARTIAL

本地提交 `72140e8ea7ed99ecb0e668c632a4247305231d3d`。报告和 manifest 明确区分全窗口 diagnostic `n=335` 与 #24 `ECG_VALID primary n=325`；10 个 ECG_INVALID 只作为 supporting，2 个 coverage/reference caveat 未与 invalid 重复计数。内部 harmonic guard 的真实调用边界和 external RSP A/B diagnostic 均有记录，没有 hard rejection 或 producer 修改。该结果只可作 supporting retrospective truth audit。

### #28 — PASS / PARTIAL

本地提交 `92f47305570622cd64ddd4b375b797b4614a5ce3`。实际枚举 11 个 session，6 个同时具备必需日志可审计，5 个保留为 `MISSING_REQUIRED_LOG`；97796/97994 的 frame-index 非连续性按 session 保留，未作全局 consecutive 断言。历史 tail 标为不可恢复，未来 stop-order 修复只定位未应用/未验证；旧 coverage manifest 已恢复，未覆盖旧 provenance。

## Unified current state

可整合的执行证据为 #24–#28 的本地提交，均只按 bounded diagnostic/supporting 层使用。所有结果均不得提升 HR/BR formal validity；当前正式边界仍是 targeted diagnostic/supporting evidence，HR `HOLD`、HRV `BLOCKED`。本轮没有远端写入，没有 producer/raw/firmware/portable V2/NIR/RGB 修改，没有 C2B/C2C 重跑，没有新 HR 算法族或 MAE 调参。

逐项证据矩阵见 `MMWAVE_ISSUE29_EXECUTION_EVIDENCE_MATRIX.csv`，机器可读汇总见 `MMWAVE_ISSUE29_SUPERVISOR_MANIFEST.json`。
