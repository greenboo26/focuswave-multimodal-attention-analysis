# Task 2S：Lei 2025 SSA 呼吸谐波去除验证结果

Status: `PARTIAL_DEVELOPMENT_ONLY_STOP_PHYSIOLOGY_RND`

执行日期：2026-08-27  
分支：`codex/mmwave-formal-reanalysis-v2`  
配置哈希：`76d1913c6bf1d1907e0b48b6841965a80373b3939ab4db96dd0d0f032ae7478a`

## 范围与边界

本轮严格使用 AgeBalanced development 30 participants 的 60 个 Rest sessions，60 s / 5 s、10 Hz、`ecg_reference_v1`。实际只有 14 个 session 具备完整 60 s 窗口；其中 12 个窗口通过 ECG QC 并被评分，另 2 个因 ECG QC 失败被拒绝。没有访问 held-out 80 人、正式 `J:\Data`、RSP 或 HRV。

AgeBalanced 本批次没有 RSP，因此呼吸频率、呼吸谐波误锁和 BR 不能被金标准验证；相关字段统一为 `NOT_ASSESSABLE_WITHOUT_RSP`，不是零误锁。

## A/B 结果

| 指标 | A 项目历史路线 | B Lei 2025 SSA 核心适配路线 | B-A |
|---|---:|---:|---:|
| attempted | 14 | 14 | 0 |
| scored | 12 | 12 | 0 |
| coverage | 85.71% | 85.71% | 0 |
| MAE (BPM) | 37.1163 | 38.0582 | +0.9419 |
| median AE (BPM) | 22.1045 | 17.8957 | -4.2088 |
| RMSE (BPM) | 49.1288 | 52.1817 | +3.0529 |
| Pearson r | 0.5123 | 0.2470 | -0.2653 |
| Spearman rho | 0.2448 | 0.1329 | -0.1119 |
| Bland–Altman bias (BPM) | -35.0366 | -36.4949 | -1.4583 |
| P90 AE (BPM) | 77.1656 | 84.7620 | +7.5964 |
| absolute error ≥30 BPM | 5 | 5 | 0 |
| half-frequency locks | 0 | 2 | +2 |

质量分层样本很小：A high/medium 为 9/3 个，MAE 38.4293/33.1772 BPM；B 为 9/3 个，MAE 39.2246/34.5591 BPM。没有 low-quality scored window。

## 方法实现与证据边界

B 实现了论文公开的核心结构：`L=floor(n/2)`；第一次 SSA 前两个分量重构呼吸基频；按无 ECG 的 `0.1–0.7 Hz` 频带估计 `fr`；加入 `2fr/3fr`；第二次 SSA 识别并移除每个目标最多两个高功率相近分量；按全部奇异值均值去除低贡献分量。由于作者代码不可得，论文未唯一给出增强正弦的幅度/相位和精确分量索引规则，本轮预先冻结了非 ECG 驱动的最小适配规则，并在每个输出中保留 `MISSING_EVIDENCE`。

论文来源：Lei et al., *Digital Signal Processing* 157 (2025), DOI [10.1016/j.dsp.2024.104911](https://doi.org/10.1016/j.dsp.2024.104911)。该来源支持 SSA 主动增强呼吸谐波后再分解的总体结构，但不提供本项目所需的作者代码或全部机器可读参数，因此本轮不得称为官方复现。

## 决策

本轮没有达到 Task 2S 规定的“约 20% 以上、在 MAE/median/RMSE/相关性中一致改善，同时覆盖率保持”的推进门槛：MAE、RMSE、相关性和 P90 均恶化，median AE 单项改善，coverage 不变，half-frequency locks 增加。因此建议：

`STOP_PHYSIOLOGY_RND`

该建议仅针对当前 AgeBalanced development 的 HR 生理路线，不是对毫米波信号层或多模态产品线的否定。下一轮不自动进入 80 人；如需继续，必须由新的明确任务重新授权并先处理本轮小样本/60 s 完整记录限制和剩余 `MISSING_EVIDENCE`。

## 可追溯产物

- runner：`scripts/mmwave_reanalysis_v2/run_task2s_lei2025_60s_v1.py`
- method：`pipelines/mmwave/lei2025_ssa_harmonic_removal_v1.py`
- config：`configs/mmwave_reanalysis_v2/task2s_lei2025_ssa_harmonic_removal_v1.json`
- schema outputs：`D:\Project\厚粲杯\11_数据\derived\mmwave_reanalysis_v2_task2s_lei2025_60s_20260827_schema\method_native_lei2025_60s_project_rows.jsonl` 与 `method_native_lei2025_60s_lei_rows.jsonl`
- summary：`D:\Project\厚粲杯\11_数据\derived\mmwave_reanalysis_v2_task2s_lei2025_60s_20260827_schema\task2s_summary.json`
