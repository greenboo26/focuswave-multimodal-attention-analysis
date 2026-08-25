# C1b：VS_DATASET 正式 benchmark 数据获取状态

更新时间：2026-08-25

## 当前状态

`C1b protocol-ready / data-access blocked`

C1a 的预检、适配器和评价协议已经完成并在本分支固化。C1b 尚未进行 24 被试正式 benchmark，因为正式 healthy cohort 的 MAT、Mindray reference 和 subject metadata 当前没有落在本机，也没有在本次任务中下载。

## 实际核验

- `https://github.com/Rc-W024/VS_DATASET` 当前 HEAD：`8551e67385e400a884335fef322b3734aadd0bf0`。
- 该 GitHub 代码快照包含 MATLAB 代码、说明和验证文件，但没有 `VITALSENSE_120_DATASET.zip`、`VS01...VS24` healthy cohort MAT 或完整 reference 数据。
- 预检报告记录的 IEEE DataPort DOI、Catalan repository DOI 和公开数据入口仍需在对应平台核验实际下载权限、文件清单、许可和校验信息。

## 不能做的事情

在正式数据取得前，不得：

- 用 VitalSense2024 的 12 个示例替代 VS_DATASET 的 24 被试 benchmark；
- 把单记录 smoke test 写成跨被试性能结果；
- 宣称 C1b 已完成，或宣称 HR/IBI/HRV 已验证；
- 为了提高 smoke-test 匹配率修改 `±75 ms`、时延估计或算法参数。

## 取得数据后的固定入口

正式数据到位后，先做数据清单、subject/session/reference 字段和原始时间戳校验，再在冻结协议下运行：

1. 本项目毫米波逐搏算法；
2. VitalSense matched-filter baseline。

两者使用同一 ECG Lead II R-peak、同一 session/device alignment、预先规定的 electromechanical-delay 处理、同一一对一匹配规则和 subject-disjoint split。正式运行前必须生成 `RUN_ID`、输入清单、配置快照和 QC 记录。
