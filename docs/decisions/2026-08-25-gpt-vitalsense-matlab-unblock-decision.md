# GPT 裁决：VitalSense 官方复现的 MATLAB 环境解锁

日期：2026-08-25
依据：`docs/decisions/2026-08-25-vitalsense-official-reproduction-handoff.md`
当前状态：`OFFICIAL_REPRO_TECHNICAL_BLOCKER`

## 结论

当前阻塞仅为本机缺少可执行的 MATLAB 环境。数据、官方仓库、官方 commit、现有 C1b ECG evaluator、评价容差和六环节差异表均已准备完成。

**不得在 MATLAB 环境到位后重新做仓库 clone、六环节差异审计、VS_DATASET 下载、ECG R 峰设计或评价协议设计。应从官方 sample 执行点直接恢复。**

## 所需环境

必须有：

- MATLAB 本体；
- Signal Processing Toolbox；
- 能执行官方 VitalSense2024 commit `d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6` 中 `.m` 源代码的许可环境。

MATLAB Runtime 不能作为本任务的替代环境，因为本任务需要直接执行和记录官方 `.m` 源代码流程。

GNU Octave 也不作为 primary reproduction 环境；即使未来用于兼容性测试，也不能替代 MATLAB 官方复现结果。

## 环境到位后的恢复顺序

1. 记录 `version`、`ver` 和 `license('inuse')`；确认 Signal Processing Toolbox 可用。
2. 在官方仓库自身 sample data 上运行官方 `main.m`，不修改官方源文件；保存 console/log、HR 和 beat peaks。
3. 若 sample 原样成功，立即使用已有 adapter 将官方 MATLAB 算法批量运行于 VS01–VS24 × Resting/Apnea 共 48 场。
4. 将官方 radar beat 输出交给现有 C1b ECG evaluator；保持 ±50/75/100/150 ms，主结果 ±75 ms。
5. 与项目带通峰值 baseline、当前透明 Python VitalSense-style AMF baseline 做三方法同裁判比较。
6. 结束于 `OFFICIAL_REPRO_COMPLETE` 或具体的 `OFFICIAL_REPRO_TECHNICAL_BLOCKER`，不得自动进入算法 V2。

## 禁止重复劳动

环境到位后禁止：

- 重新 clone 官方仓库；
- 重新下载 VS_DATASET；
- 重新做六环节 equivalence 表；
- 修改官方 MATLAB 源码以提高性能；
- 用 Python 重写版代替官方 MATLAB；
- 改 ECG R 峰算法；
- 改 beat matching 容差；
- 逐 subject/session/window 调 delay。

## 当前最短解锁动作

优先检查用户所在学校/机构是否已有 MathWorks 校园许可，并通过机构邮箱关联 MATLAB Online 或桌面 MATLAB。若机构许可可用，优先使用该许可；否则再选择个人学生许可等合法 MATLAB 环境。
