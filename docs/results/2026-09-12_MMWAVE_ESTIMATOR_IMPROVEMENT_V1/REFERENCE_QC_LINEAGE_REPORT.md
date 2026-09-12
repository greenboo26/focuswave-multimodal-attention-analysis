# 参考与质量控制来源链报告

## 判定

`PASS / REFERENCE_QC_LINEAGE_RECONCILED`.

- 当前精确分母：5 场、100 个探针、探针前 30 秒；毫米波时间源为动态链接库（Dynamic Link Library [DLL]）主机接收/入队时间。
- 严格心电图（electrocardiography [ECG]）来源：既有 `gold_standard_qa.py` 产物 `ecg_rsp_goldclean_reaudit_v1`。其 key 与 P2 为 100/100 精确一致，本任务没有改变或重算 ECG 阈值。
- ECG 资格：有效 100、无效 0、未解析 0；因此严格参考重归因仍保留全部 100 个探针。
- 呼吸带（respiration belt [RSP]）质量：基本可用 95/100，严格可用 79/100。RSP 不合格窗口继续保留，不用于删除 ECG 有效的心率比较。
- 毫米波精确窗口来源链：100/100 均保留帧数/哈希、心搏波形哈希、目标距离单元/通道、可用比例、相位稳定性、运动代理与门控字段。正式生命体征 QC 只提供质量规则来源，不替代 ECG 准确性判断。
- P2 严格参考计数：{"CORRECT_OR_NEAR_CORRECT": 39, "HARMONIC_OR_HALF_DOUBLE_LOCK": 18, "SELECTED_TARGET_WRONG_PEAK": 27, "TARGET_BIN_CHANNEL_MISS": 16}。主路线仍为估计器、峰值、谐波与融合修复，而非转为 target-only 路线。

历史 60 秒资产与 3 场/335 窗资产只作为来源链证据，未被套用到不相同窗口。
