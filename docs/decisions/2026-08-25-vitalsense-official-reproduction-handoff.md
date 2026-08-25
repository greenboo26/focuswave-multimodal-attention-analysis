# C1B official VitalSense reproduction handoff

状态：`OFFICIAL_REPRO_TECHNICAL_BLOCKER`

本轮目标是回答：当前 Python VitalSense/AMF baseline 是否等价复现官方 MATLAB VitalSense2024，以及官方 MATLAB 在同一 24 人 Radar–ECG 数据上的表现。

已完成：

1. 官方仓库已原样 clone 到：

   `D:\Project\厚粲杯\08_算法_worktrees\gpt-codex-handoff-20260825\external\vendor\VitalSense2024`

2. 官方 commit：

   `d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6`

3. 官方源代码未修改。
4. 已完成六环节等价性差异表：

   `docs/research/2026-08-25-vitalsense-official-reproduction-v1/official_vs_python_equivalence.csv`

5. 已确认当前 Python AMF 不是官方 MATLAB 的完整等价复现，六个环节均存在实质差异。

具体阻塞：本机未发现 MATLAB、MATLAB Runtime 或 Octave 可执行环境，也没有可用 MATLAB toolbox。因此无法执行官方 `main.m` sample，也不能开始 48 场正式官方复现。

本轮没有：

- 修改官方算法；
- 修改 ECG R 峰检测；
- 修改 ±50/75/100/150 ms 匹配规则；
- 重新下载 VS_DATASET；
- 重新恢复 subject/session；
- 用 Python 结果冒充官方 MATLAB 结果；
- 上传 MAT 或逐搏大表。

完整报告、环境记录、官方仓库 manifest 和 run manifest 位于：

`docs/research/2026-08-25-vitalsense-official-reproduction-v1/`

下一步只能在具备 MATLAB 环境的机器上继续：先运行官方 sample，再做 VS01–VS24 × Resting/Apnea，并把官方峰位置重新交给现有 C1b ECG evaluator。当前不进入算法优化或 V2 开发。
