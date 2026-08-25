# 2026-08-25 下午汇合证据：毫米波路线待裁决

## 使用方式

本文档用于交给 Sol 做科研路线裁决。它记录已经完成的证据，不预先替代 Sol 的判断，也不构成正式 HR、BR 或 HRV 结果。

## 线路 B：四个毫米波双门控分片

输入范围严格限定为：`sub-078-middle`、`sub-078-last`、`sub-091-middle`、`sub-091-last`。没有扫描其他 26 场，没有解码 RGB/NIR 视频，没有计算正式 HRV，没有修改正式算法主链。每个约 10 秒目标分片使用前后上下文，实际上下文约 29.46–40.00 秒。

| 分片 | HR通道SD | BR通道SD | HR子窗范围中位数 | 呼吸谐波嫌疑 | 备注 |
|---|---:|---:|---:|---|---|
| 078-middle | 1.59 bpm | 5.83 bpm | 1.50 bpm | 7/8 接近 2×BR | HR约48、BR约22.5的候选关系可疑 |
| 078-last | 7.88 bpm | 2.38 bpm | 6.00 bpm | 0/8 | HR通道离散度较大 |
| 091-middle | 6.74 bpm | 0.00 bpm | 15.00 bpm | 1/8 接近 3×BR | HR子窗不稳定 |
| 091-last | 6.04 bpm | 0.00 bpm | 10.84 bpm | 5/8 接近 3×BR | 上下文仅29.46秒，证据更弱 |

当前证据支持的最低结论：四个分片都是探索性 HR/BR 候选，但没有一个满足“可扩大验证并作为正式生理指标”的质量条件。呼吸谐波混淆和子窗不稳定是主要风险。

完整结果保存在本地，不上传大文件：

`D:\Project\厚粲杯\11_数据\derived\j_gated_hr_br_validation_v1_agent_retry\`

包括 `line_b_retry_summary.csv`、`line_b_retry_8channel_candidates.csv`、`method_manifest.json` 和复现脚本。

## 线路 C：NIR 接入预审

- 发现 58 个 subject run 目录。
- 55 个 run 同时具有 `frames.csv`、`eyes.csv`、`summary.json`、`run_manifest.json`。
- `completion.json` 59 个，`phase_windows.json` 56 个，说明完成状态和阶段文件存在覆盖差异。
- `eyes.csv` 已有正式字段和绝对 `unix_ms`，但没有完整的 `session/probe_id/window_id` 主键。
- 进入融合前必须通过独立事件表，以已核验的 `subject + session + probe_id` 和绝对 `unix_ms` 重建窗口及 alignment audit。
- `pupil_equiv_diameter` 只能解释为标准化 ROI 像素量，不能写成毫米。
- 状态：`PRECHECK_READY_WITH_GATES`，可进入完成性 QC，尚不可直接融合。

本地证据目录：

`D:\Project\厚粲杯\11_数据\derived\nir_integration_preflight_v1\`

## 线路 D：多模态接入预检

- 行为与毫米波按 `(subject, probe_id)` 成功匹配 1,297 行；毫米波多出的 20 行全部来自 `sub-099`。
- RGB 时间戳覆盖 72/72 场、1,440/1,440 探针；最近帧与行为探针最大误差 0.036 s。
- RGB 最大帧间隔 7.586 s，必须保留为质量变量。
- 现有 RGB 运动特征仅覆盖 3 场、52 窗口，不能作为全队列正式融合特征。
- 当前 `subject` 是场次标识，不是已恢复的真实人员 ID；目前不能宣称人员级 LOSO。
- 可复用 `build_evaluate_j_mmwave_m1_loso.py` 的整场次留出、防泄漏拟合和簇级 bootstrap 结构；旧 `evaluate_j_multimodal_loso.py` 不作为正式入口。
- NIR 接口冻结为 `(subject, probe_id)` 主键，窗口为 `[probe_onset_ms-60000 ms, probe_onset_ms)`，只允许正式 `eyes.csv` 测量族，禁止旧暗区/Hough proxy。

本地证据目录：

`D:\Project\厚粲杯\11_数据\derived\multimodal_analysis_preflight_v1\`

## 请 Sol 裁决的问题

请根据上述证据判断：

1. 毫米波路线应否继续扩大 HR/BR 验证？
2. 是否应停止毫米波正式 HRV 路线，转为 `raw phase/micromotion + Q0 quality descriptors`？
3. 是否保留探索性 HR/BR 作为补充结果，但不作正式生理有效性结论？
4. 报告中应如何准确表述四个分片的结果和限制？
5. 今天是否还有必要重算毫米波，还是冻结当前证据并转入报告/多模态 QC？

裁决不得因为截止期而降低质量标准。Sol 需要明确区分“目标锁定证据”“HR/BR候选”“生理有效性”和“HRV正式结论”。
