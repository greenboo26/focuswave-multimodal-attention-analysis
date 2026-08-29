# MMwave targeted validation report — 2026-08-30

状态：`PASS / MMWAVE_MERGE_READY_CONTRACT_FROZEN`

本报告严格执行 canonical `main` 的 `MMWAVE_NEXT_EXECUTION_PROMPT_2026-08-29.md`，基线提交为 `640cacea31ee54a63de348ddf11ba87834cb0db6`。本轮没有运行 Issue #16、C2B/C2C、全量 formal batch，也没有修改 NIR/RGB 或 `kyandi233-dev/Attention-Analysis@codex/formal-analysis-v2-portable`。

## 1. 工程状态先行结论

正式固件身份已由操作者确认：`mrs6240_p2512.img`，SHA256 `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`，正式采集全程使用该 identified image。机器级 burn/boot/version receipt 仍缺失，因此状态为 `CONFIRMED_WITH_PROVENANCE_LIMITATION`，不是“未绑定”。其余 device/firmware 项目保持显式证据状态，不将 SDK/manual 能力写成 formal runtime fact：window framing、zero-padding/scaling、IQ/phase calibration、TDM timing、formal-path phase compensation 仍为 `UNRESOLVED` 或 `SDK/MANUAL_ONLY`；logical Tx/Rx output semantics 已确认，DC support 只有 SDK/manual 支持证据。

工程门的本轮决策是“分类关闭、风险保留”：没有必要的正式烧录或采集动作被授权，也没有用缺失 receipt 反向否定操作者确认。上述 unresolved 项不进入 physiological merge-ready claim。

## 2. Continuity targeted validation

### 范围与方法

- 代表场次：`97793`（相对较好既有对照）、`9779`（稳定/中等）、`97795`（既有半频/谐波风险）。
- 每场只读取首 `6000` frames，使用五个重叠窗口：`0–2000`、`1000–3000`、`2000–4000`、`3000–5000`、`4000–6000`；按 100 Hz 报告为 0–20、10–30、20–40、30–50、40–60 s。
- 复用当前 `select_separate_channels_bins` 的既有候选评分和 argmax 选择，仅增加诊断输出；未加入 tracker、AoA、beamforming、multi-bin、VMD 或 target-lock 算法。
- 37 mm 只用于报告 bin displacement 的物理量换算，不改变当前算法选择。
- phase jump 只有在相邻窗口 HR bin/channel 完全相同才比较 raw complex boundary delta；本样本没有可比 transition。没有独立 motion evidence，因此不做“无运动”或“由参与者运动造成”的推断。

### 结果

| 指标 | 结果 |
|---|---:|
| session × window | 3 × 5 = 15 |
| adjacent transitions | 12 |
| HR bin hops | 8/12 = 66.7% |
| BR bin hops | 9/12 = 75.0% |
| HR channel switches | 11/12 = 91.7% |
| BR channel switches | 9/12 = 75.0% |
| same-target transitions available for phase comparison | 0/12 |
| phase jump flags > 1 rad | 0/0 comparable |

### 判定

Target/bin/channel continuity 在这个 prespecified small sample 中不稳定，不能关闭 continuity blocker。现有 phase-stability 数值只能作为 signal-selection proxy，不能替代跨窗 phase continuity，也不能被解释为 motion-artifact ratio。最小决策是保留 diagnostic continuity QC 并将 HR/BR physiological features 标为 `HOLD`；不开发新的 target tracking 路线，不启动 full batch。

## 3. Respiration harmonic A/B/C

A、B、C 使用同一组 15 个 elapsed-time windows 和同一批 `.acq` ECG/RSP reference windows。A 使用现有无外部先验的 current output；`97793` 的 A 窗口来自既有 full-session current output 的首 60 s course，`9779`/`97795` 来自既有 60 s selection output，这一 source-scope 差异已保留在 manifest，不能扩大成 full-cohort validation。

- **A — CURRENT**：读取 current radar HR。
- **B — RADAR_INTERNAL_BR_GUARD**：只读取 radar 自身 BR；若 A HR 距 2×/3× radar BR 不超过 ±5 bpm，则仅在 radar time candidate 本身不落入同一 harmonic 时使用该 radar candidate，否则 diagnostic reject。B 不读取 ECG/RSP，也未写入 producer。
- **C — EXTERNAL_RSP_DIAGNOSTIC**：只用同步外部 RSP 标记 2×/3× 关系，作为 validation oracle；不产生生产输入。

| 方法 | 有效误差窗 | coverage | MAE (bpm) | median AE | p95 AE | max AE | external-RSP harmonic 窗 MAE | non-harmonic 窗 MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 15 | 100% | 9.392 | 3.148 | 27.664 | 32.419 | 27.336 (n=3) | 4.907 (n=12) |
| B | 15 | 100% | 9.392 | 3.148 | 27.664 | 32.419 | 27.336 (n=3) | 4.907 (n=12) |

B 在 15 个窗中没有触发、没有 candidate change、没有 reject；相对 A 为 `unchanged`，不是稳定改善。故 `B_not_proposed_for_producer_from_this_targeted_sample`。C 明确显示 3 个 3× external-RSP 关系窗，但 C 的 reference 值只用于标记/解释，`C_is_production_input=false`。

本项目没有冻结的 catastrophic-error 定义，因此只报告 median/p95/max，不新增 catastrophic threshold。上述结果足以证明本轮 harmonic activation 已被诊断性验证，但不足以把 B 升级为正式 producer suppression。

## 4. Frozen mmWave merge contract

下表是面向 portable V2 external-producer-then-ingest 的唯一接入裁决。`missing` 不等于 0，也不等于 success；participant/session identity、HR/RR 分列，外部 ECG/RSP reference 不进入最终 feature table。

| feature / QC | decision | 接入边界 |
|---|---|---|
| HR | `HOLD` | 保留 current HR 作为 diagnostic/supporting 输出；target continuity 未稳定，不能作为 formal physiological feature 默认放行。 |
| BR/RR | `HOLD` | 保留 radar-derived BR/RR 供 QC/sensitivity；不因外部 RSP 诊断而放行为 validated physiology。 |
| HRV/IBI | `EXCLUDE` | 继续 `BLOCKED`；最早 blocker 是 radar beat ↔ ECG R-peak synchronization 与 paired IBI agreement 缺失。 |
| target/bin/channel continuity QC | `HOLD` | 允许作为 diagnostic QC 列；本轮证明 switching frequent，不能当作已通过质量门。 |
| phase stability QC | `HOLD` | 只能作为 phase roughness/jump proxy；本轮没有 same-target phase transition 可比证据。 |
| motion/QC proxy | `HOLD` | 本轮无独立 motion evidence；不得把 phase/selection failure 写成 participant movement。 |
| missing/loadability status | `ALLOW` | 允许作为结构/可加载性元数据：当前 portable contract 的 44 registered / 39 loadable / 33 groups / 5 structural missing，保持 missing ≠ 0 ≠ success。 |
| external ECG/RSP values | `EXCLUDE` | ECG/RSP 仅作 A/B/C validation reference，不进入最终 mmWave producer 特征。 |

这意味着 contract 已冻结，但 physiological HR/BR 不被伪装成已验证；portable 分支可按其既定 standardized-table 和 missingness contract 接收受控字段，不能在本轮直接宣称正式 HR/BR 生理融合完成。

## 5. Evidence and reproducibility record

- Diagnostic code: `scripts/maintenance/run_mmwave_targeted_validation_20260830.py`。
- Continuity table: `target_continuity_diagnostic.csv`。
- A/B/C table: `harmonic_abc_window_metrics.csv`。
- Run manifest and SHA256: `run_manifest.json`。
- Summary JSONs: `target_continuity_summary.json` and `harmonic_abc_summary.json`。
- Producer reference commit: `640cacea31ee54a63de348ddf11ba87834cb0db6`。
- Raw data were read in place and not copied, renamed, modified, or uploaded.

最终保持：`HRV = BLOCKED`；`ISSUE_16 = PAUSED`。
