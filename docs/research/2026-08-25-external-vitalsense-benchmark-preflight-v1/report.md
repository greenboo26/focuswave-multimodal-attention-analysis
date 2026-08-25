# VS_DATASET + ECG 毫米波逐搏/IBI benchmark 预检 v1

## 结论

预检已建立可复核的外部基准入口与单文件适配 smoke test，但 **VS_DATASET 正式 healthy cohort 的 MAT、subject metadata 和 reference 文件未在本机，也没有在本任务中下载**，因此尚未执行 VS_DATASET 的正式逐搏/IBI benchmark，更没有训练、跨被试统计或性能结论。

VitalSense2024 仓库自带的一个 ECG 示例可被无交互地读取、转换为雷达帧级 vital signal、产生暂定峰时间戳并按预注册式的固定 0 s 对齐与 75 ms 容差评价。该成功仅验证了“MAT 布局和端到端 I/O 可运行”，不验证 ECG R 峰质量、机械脉搏相对 R 峰的生理时延、算法性能或对 VS_DATASET 的可迁移性。

## 实际审计与读取范围

公开来源均已浅克隆到 `source_snapshots/`，并固定提交：

| 仓库 | 实际读取文件 | 审计要点 |
| --- | --- | --- |
| VS_DATASET `8551e...0bf0` | `LICENSE`, `README.md`, `HEALTHY.md`, `PATIENT.md`, `VS_separation.m`, `TechValidation.m`, `PlotVS.m`, `VitalSig_HUGTiP.m`, `Technical_validation_results.csv` | healthy/patient 布局、MIT、雷达/ECG/RSP 字段、同步实现、原始二通道 BIN 解码 |
| VitalSense2024 `d9f71f...6de6` | `LICENSE`, `README.md`, `main.m`, `HRestim.m`, `plotPhase.m`，以及 `data/C_chest_normal_withECG.mat` 的变量头和实际数据 | MIT、原始 ADC/帧参数、信号分离、FFT/自相关周期选择、template/reverse-template matched filter、峰时间戳 |

文件级原始链接及用途在 `source_manifest.csv` / `source_manifest.json`。仓库内 `AlazarTech/` 是采集 SDK；其许可与硬件运行不是本次离线预检依赖，未执行。

## 数据可用性与字段证据

完整说明见 `data_schema_or_access_status.md`。关键边界如下：

* **VS_DATASET healthy**：文档描述 24 人、Resting/Apnea、雷达 MAT + Mindray MAT。已由 MATLAB 代码确认预期字段：雷达 `VitalSig`, `T_frame`, `Radar.t_frame`, `Radar.fs`；reference `ecg_lead2`, `Fs_ecg`, `respiration`, `Fs_resp`，绘图还引用 pleth/其采样率和其他 ECG leads。正式 MAT 未在快照中，故字段为“代码期望”，不是本机数据验证。
* **VS_DATASET patient**：文档标为 under construction，说明约 87 GB；代码可读取同 ADC 两通道 raw BIN（CH1 radar，CH2 ECG Lead II），但公开 patient data 未下载，不能预先假定每会话实际可用。
* **VitalSense2024 示例**：`data/` 有 12 个 MAT；实测 `beatingTone_time=(512,8000)`、`data=(1,4096000)`，其中 5 个另含 `ECGSignal=(1,4096000)`。没有 RSP、pleth、subject/session metadata，不能代替 VS_DATASET 的正式 cohort。

公开正式访问入口已记录但未下载：healthy [IEEE DataPort](https://doi.org/10.21227/wq68-sv85) 与 [Catalan repository](https://doi.org/10.34810/data2962)，patient [figshare](https://figshare.com/s/e056be5dd8bfee45dd6c)。使用它们前仍需核验数据许可、实际文件清单和 reference 字段。

## 已核验的代码路线

### VS_DATASET

`VS_separation.m` 对 MAT 中的 `VitalSig` 用 300 阶、0.3 Hz FIR `filtfilt` 取得呼吸低频项，以残差取得 cardiac signal，并只作与 `ecg_lead2` 的可视化。它没有逐搏匹配、IBI 或 HRV 指标。

`TechValidation.m` 以 RSP（非 ECG）把 reference 和 radar 重采样到 2000 Hz，`xcorr` 最大点作为全会话同步 lag。注意其 `results.maxCorr(idx)=lag_max`：变量名是 maxCorr，实际存入的却是 lag 样点数；随附 CSV 也反映该实现。因此预检接口将其视为“可复算的 lag 候选”，不会将其视为相关系数，也不会把峰级 ECG 调整反向用于同步。

`VitalSig_HUGTiP.m` 是 patient raw-BIN 路线：读 4 个 `uint32` header、读 `uint16` payload，通道 1 雷达、通道 2 ECG；采用 122 GHz、3 ms（333.33 Hz frame）和 1024 chirp samples/683.6 kHz ADC 的配置，单-bin DFT 后解相位为 radar vital displacement。它仅展示 ECG，未给出逐搏评分。

### VitalSense2024 baseline

实际读取的 `main.m` 不止 README：

1. Hann-window FFT 在测距 bin 定位目标，取相位解缠为 vital displacement；配置为 122 GHz、3 ms frame。含 ECG 的 MAT 由 `ECGSignal(1:Digitizer.long:end)` 降至帧率。
2. 300 阶 0.3 Hz FIR 低通分离呼吸，cardiac residual 再清除前 40 个 FFT bin。
3. 40–200 bpm 的频谱候选由 `HRestim` 使用频谱与自相关做 period 选择（`HRestim.m` 的候选窗口又是 40–130 bpm）。
4. 先以正弦/三角/矩形的 period filter 取得粗峰，围绕它们平均得到 pulse template；反转 template 后卷积，即 adaptive matched filter；随后 `findpeaks` 输出 `locs_hsig`，这就是可接入逐搏/IBI 接口的 radar heartbeat timestamps。

该路线本身会使用数据依赖 template 和手调 `MinPeakProminence`，而且未定义统一的 ECG R-peak、跨 session split 或逐搏容差。因此它是可比处理骨架，而不是可直接报告逐搏基准的完整 baseline。

## 固定的 beat-level benchmark 协议

权威定义位于 `pipeline_manifest.json`：

| 项目 | 固定规则 |
| --- | --- |
| ECG reference | Lead II 的经过预定义 QC 的 R-peak 时间戳；不把监护仪输出 HR 当 ground truth |
| 同步 | 有原始时戳时直接使用；否则只可用独立 RSP 等同步通道得到 session-level lag，并在逐搏评分前冻结。VitalSense2024 smoke test 为同 ADC sample index、0 s lag |
| matching | 时间顺序的一对一 greedy match，禁止重复配对或对每个 beat 搜索偏移 |
| 容差 | ±75 ms，作为 v1 固定主分析；如需灵敏度分析必须另报 ±50/±100 ms，不取最优值 |
| HR error | `abs(60/median(IBI_radar) - 60/median(IBI_ECG))`，单位 bpm |
| matched IBI error | 相邻的连续已匹配 radar/reference beat pair 的 IBI 差，报告 MAE 与 bias，单位 ms |
| recall/precision | matched/reference eligible beats；matched/radar eligible beats |
| RMSSD/SDNN error | 从 matched IBI 序列分别计算，取雷达和 ECG 的绝对差，单位 ms；有效 IBI 数不足时 NA |
| split | subject-disjoint。一个 subject 的全部 session/scenario 仅在一个 split；调参只在 train subjects，不能随机切 window |

与 VitalSense route 的共同接口是：phase vital signal、0.3 Hz separation、FFT/自相关 period proposal、radar template matched filter、`findpeaks` timestamps。新增且必须保留的外部 benchmark 接口是 frozen ECG alignment、one-to-one matching、subject/session provenance、IBI/HRV 与 QC。未复现 baseline 的手工阈值、图中数字或论文性能。

## 实际运行与结果边界

实际执行命令：

```powershell
python run_single_case_preflight.py --input-mat source_snapshots/VitalSense2024/data/C_chest_normal_withECG.mat --output-json single_case_smoke_test.json
```

运行完成，依赖为 Python + SciPy 1.17.0；输出在 `single_case_smoke_test.json`。它读到 8000 帧（24 s）雷达和等长原始 ECG，生成 72 个暂定 ECG peaks、31 个 radar peaks、7 个 75 ms 内匹配；其完整数值仅保存在 JSON 作可重复的 smoke-test log。**这些数值不得作为 HR、IBI、HRV 性能或与论文 baseline 的比较结果。** 原因是通用 ECG `find_peaks` 未经 R-peak 标注验证，固定零时延忽略 ECG 电活动和雷达机械脉搏的生理相位差，并且只有一个未标识 subject/session 的示例。

未运行 MATLAB、未运行 VS_DATASET 的 `TechValidation.m` 或 `VS_separation.m`，也未下载 DataPort/figshare 文件、更未进行任何训练或批处理。

## 最小下一步

1. 在单独数据根获取 healthy MAT + `Subject Information.xlsx`，先运行只读 schema audit：每个 session 的字段、采样率、长度、绝对/相对时间、RSP sync coverage、ECG quality 与 subject ID。
2. 将 `run_single_case_preflight.py` 的 MAT adapter 改为每会话输入，输出 `radar_beats.csv`、`ecg_beats.csv`、alignment/QC record；RSP-derived session lag 必须先生成并冻结。
3. 在至少两个开发 subject 仅确定 ECG detector/QC 与 matched-filter 阈值后，按 subject-disjoint held-out subjects 报告上述五类指标及 subject bootstrap CI；不把 VitalSense2024 示例混入正式估计。

## 变更边界与验证

所有新增文件仅写入本目录及其 `source_snapshots/`；没有改动 `08_算法` 正式链、NIR、RS6240 原始数据、J 盘 target-lock 或已有正式结果，没有创建 Sol 子任务，也没有 Git push。产物完整性已通过 JSON 解析、Python 编译和指定 smoke test 复跑检查。
