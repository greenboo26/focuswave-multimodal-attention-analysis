# Formal mmWave Tier 重算：corrected 37 mm 距离 QC

状态：PASS（只做既有 QC 表重算；不重跑 HR/BR，不改算法）。

## 1. 重算结果

| Tier | 旧人数 | 新人数 | 新 session 列表 |
|---|---:|---:|---|
| Tier 1 | 17 | 33 | 071, 072, 074, 076, 078, 082, 083, 086, 088, 089, 091, 093, 094, 095, 096, 098, 100, 106, 107, 109, 110, 114, 116, 119, 124, 125, 126, 129, 130, 134, 139, 143, 170 |
| Tier 2 | 53 | 37 | 056, 057, 058, 059, 062, 064, 065, 068, 070, 073, 075, 077, 081, 084, 085, 087, 090, 104, 108, 117, 118, 122, 123, 127, 128, 131, 133, 145, 147, 148, 154, 158, 160, 162, 166, 175, 178 |
| Tier 3 | 2 | 2 | 067, 099 |

合计：72 个 session。

## 2. 替换规则

仅替换旧的 distance-based B 判定：

1. `corrected_distance_qc=FAIL` 作为 corrected 37 mm distance QC 条件。
2. 原有 phase stability 判定保留：`target_lock_status=plausible_distance_phase_unstable`。
3. 原有 window/probe coverage 判定保留：当前 C attribution 与原有 `window_quality_pct <80` 或 `probe_quality_pct <80` 证据不改写。
4. 067、099 的原有 A/provenance 保留为 Tier 3，不因 corrected distance QC 改变。
5. 其余满足 formal linkage、原有 coverage 门槛、原有 phase 规则未触发且 corrected distance QC 为 PASS 的 session 归入 Tier 1。

corrected QC 源表共 71 行（不含 067）：PASS=49，FAIL=22。FAIL 中 099 保留 Tier 3，127 同时保留原有 phase-stability B；因此本次实际由 corrected distance QC 直接触发/保留为 Tier 2 的 distance 条件为 20 场。

## 3. 保留的非距离条件

- phase stability 保留 8 场：070, 077, 123, 127, 133, 148, 158, 175。
- window/probe coverage C 保留 9 场：056, 058, 062, 081, 084, 104, 118, 162, 166。
- A/provenance 保留 2 场：067, 099。
- corrected distance QC 的 20 场有效 distance 条件：057, 059, 064, 065, 068, 073, 075, 085, 087, 090, 108, 117, 122, 128, 131, 145, 147, 154, 160, 178。
- 从旧 Tier 2 升至新 Tier 1 的 16 场：071, 072, 076, 086, 088, 089, 093, 096, 100, 109, 110, 116, 130, 139, 143, 170。

## 4. 实际证据位置

| 内容 | 代码/文件位置 | 实际字段或参数 |
|---|---|---|
| corrected 37 mm QC 原始既有表 | `C:/Users/550ACW/Documents/Codex/2026-08-29/rs6240-sdk-hr-br-hrv-1/outputs/FORMAL_37MM_DISTANCE_QC.csv` | `session`, `selected_bin`, `old_distance_qc`, `corrected_distance_qc`, `qc_change_type` |
| corrected QC 汇总表 | `C:/Users/550ACW/Documents/Codex/2026-08-29/b1-formal-71-corrected-target-distance/outputs/FORMAL_37MM_DISTANCE_QUALITY_BASE.csv` | `corrected_distance_0.037_m`, `corrected_distance_qc`, `phase_stability`, `window_quality_pct`, `probe_quality_pct` |
| corrected distance 生成/校验代码 | `C:/Users/550ACW/Documents/Codex/2026-08-29/b1-formal-71-corrected-target-distance/work/build_b1_distance_quality.py:11-12,132-177` | 输入源；71-session 对齐；`corrected = int(selected_bin) * 0.037`；旧/新 QC 字段原样写入 |
| corrected QC PASS/FAIL 分组 | `C:/Users/550ACW/Documents/Codex/2026-08-29/b1-formal-71-corrected-target-distance/work/build_b1_distance_quality.py:233-234` | `corrected_distance_qc == PASS/FAIL` |
| 旧 Tier 定义与边界 | `D:/Project/厚粲杯/08_算法/docs/results/mmwave_formal_vital_qc_v1/MMWAVE_FORMAL_VITAL_QC_V1.md:48-50,56` | Tier 1/2/3；旧 B 的 distance/phase/low-signal status；C 的 window/probe 条件 |
| 旧 B distance 与 phase 计数 | `D:/Project/厚粲杯/08_算法/docs/results/mmwave_formal_vital_qc_v1/MMWAVE_ALGORITHM_AND_RANGE_GATE_AUDIT_V1.md:57-68` | 旧 distance-based B=36；phase B=8；C=9 |

## 5. 边界

- 本次只读取既有 session-level QC 与 corrected 37 mm QC 表进行 Tier 重算。
- 没有重新运行 HR、BR、HRV 或 formal producer。
- 没有修改算法、阈值、target bin/channel 或原始数据。
- 旧的 `mmwave_session_use_tier_crosswalk.csv` 未覆盖；新的 corrected37mm 版本单独保存。



