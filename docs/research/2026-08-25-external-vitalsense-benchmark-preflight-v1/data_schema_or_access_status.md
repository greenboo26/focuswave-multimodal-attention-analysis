# 数据结构与访问状态

## 已实际读取的公开快照

两个 GitHub 仓库均已于 2026-08-25 浅克隆，并固定到 `source_manifest.json` 所列提交。两者根目录 `LICENSE` 均为 MIT；该许可证覆盖仓库代码，但正式数据集另有各数据平台的访问与使用条款，尚未下载或独立核验。

### VS_DATASET healthy cohort：可适配，正式 MAT 未在本机

`HEALTHY.md` 声明 24 位被试、每人 Resting 与 Apnea 各 2 分钟，预期路径为 `VSxx/VSxx_{Resting|Apnea}.mat` 与同步的 `VSxx_{Resting|Apnea}_Mindray.mat`，另有 `Subject Information.xlsx`。代码实际使用的字段为：

| 文件 | 已由代码引用的字段 | 采样/时间信息 |
| --- | --- | --- |
| radar MAT | `VitalSig`, `T_frame`, `Radar.t_frame`, `Radar.fs` | `VS_separation.m` 从文件读入；脚本中的默认帧间隔为 3 ms，即 333.33 Hz，但正式 MAT 仍须逐文件核验 |
| Mindray MAT | `ecg_lead2`, `Fs_ecg`, `respiration`, `Fs_resp`, `pleth`, `Fs_pleth`, 以及 `ecg_lead3`, `ecg_leadv1`（绘图代码） | 各 reference 采样率应由 MAT 字段读取，不能在适配器中硬编码 |

公开快照没有 `VS01...VS24` 文件夹、正式 MAT 或 Excel；因此 ECG、RSP、pleth/reference 的字段只能确认“代码预期”，不能确认正式数据实际全部存在、长度一致或质量合格。

同步路线：`TechValidation.m` 将 reference RSP 和雷达 `VitalSig` 都重采样至 2000 Hz，使用全记录 `xcorr` 最大值给出 session lag。该代码把 `lag_max` 写入 `maxCorr` 字段，故该列实际是 lag 样点数而非相关系数，不能作为 correlation quality 指标。此同步路线仅可作为非 ECG 驱动的 session 对齐候选；正式 benchmark 必须重算并保存归一化相关系数、lag 和边界/质量条件。

### VS_DATASET patient cohort：目前只记录访问入口

`PATIENT.md` 标注“UNDER CONSTRUCTION”：15 名住院患者、多次 10 分钟会话、约 87 GB，雷达为 raw `.bin`，reference 为 MAT。`VitalSig_HUGTiP.m` 明确二通道 raw BIN，通道 1 为雷达，通道 2 为同步 ECG Lead II；其 header 读为 `uint32 chans,long,recs,buffs`，数据读为 `uint16` 后 reshape。它固定 3 ms 帧周期、122 GHz、1024 chirp samples（`decimation=2`）、ADC 683.6 kHz。该病人 cohort 未下载，故这些是代码路线，非已验证数据事实。

### VitalSense2024：本机可用的最小示例

仓库 `data/` 有 12 个 MAT。实测全部拥有 `beatingTone_time (512,8000)` 和 `data (1,4096000)`；5 个文件还拥有 `ECGSignal (1,4096000)`：`C_chest_normal_withECG`、`C_legfemoral_normal_withECG`、`D_abdomen_normal_withECG`、`D_chest_normal`、`D_chest_normal_withECG`。未见 RSP、pleth、subject ID 或正式 session 元数据。`main.m` 的配置为 3 ms frame、122 GHz、512 raw samples（`decimation=4`）及 ADC 341.8 kHz；MAT 大小与 512×8000 一致。

本预检实际只读取 `C_chest_normal_withECG.mat`，未遍历或训练其余示例，也未将示例与 VS_DATASET 混作同一 cohort。
