# 厚粲杯本地资产索引与已完成工作地图

更新时间：2026-08-25  
用途：给后续 GPT/Codex 会话提供本地数据、代码、结果和状态的唯一导航入口。本文只登记路径、资产类型、已完成工作和状态，不上传原始数据。

## 重要路径纠正

用户消息中的 `11\_数据`、`08\_算法` 是转义后的写法；Windows 实际目录名为：

| 用户写法 | 实际存在路径 | 本轮是否核验 |
|---|---|---|
| `D:\Project\厚粲杯\11\_数据` | `D:\Project\厚粲杯\11_数据` | 是 |
| `D:\Project\厚粲杯\08\_算法` | `D:\Project\厚粲杯\08_算法` | 是 |
| `D:\acq\_mmwave\_data` | 不存在；未擅自把它当作其他目录 | 是 |
| — | `D:\acq_mmwave_data` | 是，当前发现的毫米波采集数据目录 |

后续引用必须使用“实际存在路径”，不得继续写不存在的路径。

## 资产总表

| 资产 | 实际路径 | 类型 | 本轮盘点规模 | 当前状态 | 已完成工作/可复用内容 |
|---|---|---|---:|---|---|
| 项目总工作区 | `D:\Project` | 多项目工作区 | 可见递归文件 70,560，约 30.58 GB | CURRENT，但不是单一算法仓库 | 包含 `厚粲杯`、`.claude`、`.codex`、`output` 等；只作为路径根，不把整个目录当作可上传仓库 |
| NIR 正式输出 | `D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR` | 大型派生结果 | 1,527 个非 `.git` 文件，约 3.30 GB | CURRENT/部分完成 | 有 `nir_formal_probe_features.csv`、`nir_formal_feature_quality.json`、`batch_run_summary.json`；当前摘要显示 2 个候选运行目录、0 个完整运行目录，正式特征行数为 0，不能把此目录写成 NIR 全量完成 |
| 毫米波采集数据 | `D:\acq_mmwave_data` | 原始/采集配套数据 | 1,286 个文件，约 19.43 GB；1,204 NPZ、49 CSV、11 ACQ、11 BIN、11 JSON | CURRENT 原始数据 | 含 `sub-2_`、`sub-3_`、`sub-4_`、`sub-5_`、`sub-6_`、`sub-9779_`、`sub-97792_`、`sub-97793_`、`sub-97795_`、`sub-97796_`、`sub-97994_`；已用于既有 ECG/RSP 校准、毫米波时间戳与质量/目标锁定相关工作；本轮未重算 |
| 正式/预实验数据总目录 | `D:\Project\厚粲杯\11_数据` | 数据与派生结果总目录 | 可见递归文件 5,788，约 11.53 GB | CURRENT | 含 `derived`、`external_benchmarks`、NIR 正式输出、外部 Radar–ECG 数据、预实验/校准资产；具体结果必须引用子目录和文件，不得只写“11_数据” |
| 预实验数据 | `I:\预实验` | 原始/采集配套数据 | 2,684 个文件，约 209.58 GB；2,521 NPZ、121 CSV、22 AVI、10 JSON、9 BIN、1 7Z | CURRENT 原始数据 | 含 10 个预实验被试目录；每个已核验目录可能含行为、毫米波、NIR、RGB 以及时间戳/元数据；本轮未解码视频、未重跑算法 |
| NIR/行为算法仓库 | `D:\Project\厚粲杯\08_算法\01_Attention-Analysis_nvidia-cuda` | Git 仓库 | 不含 `.git` 时 2,594 个文件，约 886 MB | CURRENT，分支 `nvidia-cuda`，HEAD `1d3587f` | NIR 正式管线、RITNet/YOLO 相关配置与脚本、行为分析文档和历史记录；当前工作区有未提交修改，不能把 HEAD 当作所有本地改动已同步 |
| mmWave/ECG/项目算法仓库 | `D:\Project\厚粲杯\08_算法_worktrees\gpt-codex-handoff-20260825` | Git worktree | 以 Git 状态为准 | CURRENT 交接 worktree，HEAD `97b236a` | C1b VS_DATASET benchmark 入口、协议、总账和交接裁决；本地提交已完成，原始 MAT 和大体量派生结果留在 `11_数据` 外部 |

## NIR 当前具体状态

权威正式输出目录：

`D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR`

已发现的关键文件：

- `batch_run_summary.json`：当前候选运行目录和完成状态摘要；
- `nir_formal_feature_quality.json`：质量汇总；当前记录 `candidate_run_dirs=2`、`complete_run_dirs=0`、`feature_rows=0`；
- `nir_formal_probe_features.csv`：正式特征输出入口，目前不能按“已有完整特征”解释；
- 各运行目录下的 `completion.json`、`phase_windows.json`、`frames.csv`、`eyes.csv`、`summary.json`、`run_manifest.json`：逐运行追溯文件。

明显需要区分的资产：

- `smoke-sub-056\...yolo_b16_fp32_smoke60`：试运行/烟雾测试，不是正式全量结果；
- `sub-056_formal_v3.1.3_yolo_b16_fp32`：当前未完成或中断候选；
- `sub-056_formal_v3.1.3_yolo8_b16_fp32` 与 `sub-056_formal_v3.1.3_yolo_b16_fp32`：不同模型/运行版本，不能自动合并；
- `c3_nir_qc_integration_v1` 和 `beijing_sensor_increment_v1`：已有的身份映射、coverage、common-probe 及第一版增量分析派生结果，应优先复用，不因当前正式输出目录为空而重新恢复身份。

## 毫米波数据与既有工作

`D:\acq_mmwave_data` 是当前可直接找到的毫米波采集目录。其目录下的 `mmwave_timestamps.csv` 和 `*.meta.json` 是时间轴/采集元数据入口，`cal\events.csv` 是校准/事件入口，`beh\master_timeline.csv`、`events.csv` 和行为 CSV 是行为关联入口。

已经存在并应优先复用的工作包括：

1. ECG/RSP 金标准校准及算法版本核查，包含旧版与 `process_vital_signs_v3_1_1.py` 调用链区分；
2. target-lock、range-bin、8 通道空间一致性、RGB motion gate 和 J 盘分片级目标锁定审计；
3. mmWave probe 特征、M1/Q0/行为基线和 common-probe 增量比较；
4. C1b 外部 VS_DATASET Radar–Mindray ECG benchmark，结果见 `D:\Project\厚粲杯\11_数据\derived\vitalsense_c1b_benchmark_v1`。

本轮没有重新扫描 NPZ、没有解码 RGB/NIR 视频、没有重跑毫米波正式算法。

## 结果与代码边界

- GitHub 仓库保存：代码、协议、方法、决策、状态、字段清单和可复现入口。
- 本地数据目录保存：原始 MAT/NPZ/AVI、完整 CSV、逐帧输出和大型派生结果。
- 不把 `D:\Project` 整体上传；不把 `D:\acq_mmwave_data`、`I:\预实验`、NIR 全量结果或 `11_数据\derived` 整体上传。
- 需要 GPT 读取结果时，优先读取本文件、`docs/WORKSPACE_LEDGER.md`、对应 `docs/decisions/*.md` 和具体结果目录中的 `report.md`/`run_manifest.json`，不要重新扫描原始数据。

## 本轮核验限制

本轮是文件索引和状态盘点，不等于逐个阅读 70,000 个工作区文件，也不等于重新验证所有历史结论。对于每项科学结论，仍应以对应的运行清单、脚本、结果表和报告为证据；本索引的作用是避免找不到文件、重复劳动或把试运行/历史版本误当作 CURRENT。
