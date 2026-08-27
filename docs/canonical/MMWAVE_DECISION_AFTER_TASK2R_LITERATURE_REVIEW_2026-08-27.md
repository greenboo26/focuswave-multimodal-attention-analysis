# mmWave 决策更新：Task 2R 后的文献复核

Date: 2026-08-27
Status: `ACTIVE_DECISION`

## 结论

Task 2R 的 `DOWNGRADE_PHYSIOLOGY` 不作为最终结论。原因不是 Task 2R 结果无效，而是其 `SSA+VMD adapted` 并未忠实实现 Lei et al. (2025) 的核心 SSA 呼吸谐波去除流程，因此不能据此判断该目标方法无效。

当前只授权最后一次限时方法验证：Task 2S。

## 证据修正

Task 2R 实际使用固定 SSA `L=400`、固定 rank、固定 VMD `K=5/alpha=1000` 与自定义 HR-band IMF 选择。Lei 2025 原文则明确：

- SSA `L = n/2`；
- 第一次 SSA 用前两个最大奇异分量重构呼吸基频；
- 生成并加入呼吸二次、三次谐波以主动增强其能量；
- 第二次 SSA 删除对应四个谐波分量；
- 使用奇异值均值阈值做 SSA 去噪；
- 后续 EE-VMD/PCC-VMD 通过 GWO 优化 VMD 参数，而非固定 `K=5/alpha=1000`。

因此 Task 2R 的 28.12 BPM 只代表 adapted pipeline，不代表 Lei 2025 完整方法。

## 当前比赛路线

1. 30 s 仍是 FocusWave 产品主分析窗口，不因外部方法改变。
2. AgeBalanced development 30 人用于 Task 2S 的 60 s / 5 s 方法诊断；60 s 对应 Lei 论文 1 min 实验并允许 `L=n/2` 的自然实现。
3. Task 2S 只加入 Lei SSA 呼吸谐波去除/去噪核心模块，其余 HR estimator 保持一致。
4. 不做完整 PCC/EE-VMD+GWO，除非 Task 2S 出现明确实质改善。
5. 不跑 80 held-out，除非 Task 2S 先达到 `ADVANCE_LEI_PIPELINE`，并在查看 held-out 前确定最终配置。
6. HRV 当前不作为比赛必做 KPI；AgeBalanced radar 10 Hz 不承担可靠 beat-level HRV 的主验证任务。
7. 本地 RS6240+BIOPAC 保持机制/压力测试角色，不作为跨被试产品有效性主证据。
8. 如果 Task 2S 未产生约20%以上、且多指标一致的改善，则停止新的 HR/HRV 算法研发，mmWave 转入 motion/phase/spectral/quality supporting-signal 与多模态 AI 主线。

## 任务入口

- `docs/mmwave_reanalysis_v2/TASK2S_LEI2025_SSA_HARMONIC_REMOVAL.md`
- GitHub Issue #5: `Task 2S: Lei 2025 SSA harmonic-removal validation`

## 时间边界

Task 2S 硬上限 1.5–2 h。不得扩展为新的毫米波算法研究项目。
