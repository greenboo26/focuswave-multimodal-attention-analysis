# 毫米波正式生产契约加固 V1

## 基线与证据

本修复从 `codex/mmwave-formal-reanalysis-v2` 的固定提交
`d87229afe071f23450728a6d617ec82317e6c9df` 分出，不直接修改 `main`。选择该基线的原因是：
毫米波重分析代码、配置和测试位于该路线，且本地审计所核验的生产脚本哈希也来自该提交；远端
`main` 已与该路线分叉，不能在本任务中私自合并。

规范与现场证据固定引用
`kyandi233-dev/FocusWave-Formal-Analysis@171b081f3a3f9d06496c7b8d36915eebd4e2a3bb`，
尤其是“毫米波分析/1、1.1、1.2”“资产导航/1.1～1.3”“运行记录08-29-06”和“协作治理1.2”。
本文不生成真实 HR、RR 或 HRV 结论。

## 依赖和方法预检

生产 `vmd_heart` 只接受直接依赖 `vmdpy==0.2`，对应 PyPI wheel 的 SHA-256 为
`331e3013dbc95beb564fe7ce70a0f95a09efb44d0ec56a28f61e9ab40fe16c1b`。不再把
`sktime.libs.vmdpy` 当作隐式替代后端，以免不同机器在未改变方法名时使用不同实现路径。
`bp_heart` 仅在命令行显式写出 `--method bp_heart` 时运行；缺少 VMD 依赖时不会自动降级。

本仓库只锁定依赖，不代替本地用户安装。可先执行不读数据的预检：

```powershell
& 'D:\Code\python\python.exe' -u scripts/run_timeline_gated_mmwave_quality.py --preflight-only --method vmd_heart
```

退出码 0 且 `status=pass` 才能继续。缺包、版本不符或 `VMD` 符号不可导入时退出码为 2，并给出
`failure_reason`；不会切到 `bp_heart`。

## 输入、输出和迁移

正式运行现在必须传入外部冻结的 JSON/CSV session manifest。每行至少包含：

- `session_id`；
- `anonymous_participant_group_id`；
- 可选的 `repeat_participant_id`、`identity_status`、`site`、`source_tag` 和 `source_ref`。

身份键只做原样透传，不由毫米波代码推断。程序按 manifest 行数工作，不硬编码 44、39、38 或 33；
后续追加场次使用新冻结 manifest 即可。目录扫描只负责把 manifest 场次连接到本机输入。32 字节
`.bin` 加 0 字节 timestamps、空毫米波目录、无可分析 NPZ 均依据文件事实拒绝，不再依赖当前五个
场次编号的硬编码表。

输出根必须不存在或为空，防止覆盖历史结果。主要输出为：

- `crop_manifest.json/csv`：输入与时间门状态；
- `segment_analysis_summary.json`：带 schema、pipeline、input manifest 哈希和方法预检的嵌套结果；
- `segment_analysis_rows.csv`：固定的场次×segment 明细；
- 每段生产 JSON/NPZ/图形：保留在独立 segment 目录。

单段字段统一为 `breath_rate`；质量只从 `heart_rate.time_course.signal_quality` 和
`heart_rate.time_course.metrics` 提取。所有 JSON 使用 `allow_nan=false`；非有限的诊断值转为 `null`，
而全非有限候选会直接拒绝并记录 `algorithm_returned=false`、`quality_valid=false`、
`selection_status=rejected` 和 `failure_reason`，不会回落到 ch0/bin10。

每个指标分别保留“能否计算、工程质量、外部生理验证、行为关联、报告准入”五层状态。当前默认仍为：
外部验证 `not_available`、行为关联等待正式放行、报告 `blocked`；IBI/HRV 即使有候选也仅为
`candidate_only`。

## 本地 Codex 复跑步骤

先在新输出根做 `sub-031` 单场复跑。manifest 可只包含该场，但必须来自冻结映射，不得手填新身份：

```powershell
$repo='D:\AAAWORK\07-竞赛\厚璨杯\021-analysisplan\focuswave-central'
$manifest='D:\_AttentionData\mmwave_manifests\sub031_frozen_manifest.json'
$out='D:\_AttentionData\mmwave_local_execution\20260829_sub031_contract_v1'
Set-Location $repo
git fetch origin --prune
git switch codex/mmwave-production-contract-hardening
git pull --ff-only
& 'D:\Code\python\python.exe' -u scripts/run_timeline_gated_mmwave_quality.py --preflight-only --method vmd_heart
& 'D:\Code\python\python.exe' -u scripts/run_timeline_gated_mmwave_quality.py --roots 'E:\正式实验' --input-manifest $manifest --output-dir $out --run-analysis --method vmd_heart
```

若负责人只批准工程冒烟，最后一条命令必须显式改为 `--method bp_heart`，并保持方法字段为
`bp_heart`，不能把输出描述为 VMD 正式结果。

## 尚未放行

合并前仍需本地 Codex 在全新输出根完成 `sub-031` 复跑，核对 schema、严格 JSON、候选拒绝状态、
每段结果与汇总同源。通过后还需负责人单独批准当前 39 个可加载场次的正式增量运行。没有 ECG/RSP
外部参考时，HR/RR/IBI/HRV 均不得写成外部生理验证通过，也不得写入正式结果结论。
