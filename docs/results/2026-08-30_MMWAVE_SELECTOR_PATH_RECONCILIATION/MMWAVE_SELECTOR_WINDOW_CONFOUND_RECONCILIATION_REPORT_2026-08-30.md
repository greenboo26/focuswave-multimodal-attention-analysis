# Selector/path confound reconciliation for #25 — 2026-08-30

状态：`PARTIAL / WAIT_ON_SELECTOR_VALIDITY`

## 已执行的复用检查

复用既有 `MMWAVE_WINDOW_LENGTH_COMPARISON_REPORT_2026-08-30.md` 的 20 s/60 s paired diagnostic，以及本目录的 335-window canonical selector replay；没有重新选择窗口、调整 MAE、改变 ECG_VALID 分母或重跑 producer。

既有窗口比较在 283 个 paired ECG-valid windows 上给出 20 s MAE=`14.703129` bpm、60 s MAE=`5.608574` bpm，差值=`-9.094555` bpm。该比较使用固定 target/bin/channel 的 targeted path；本轮 A1 回放显示，同一固定路径没有调用 canonical `_select_spectral_bpm()` 的 previous-anchor 状态链。

## 结果与决策

在冻结 #27 分母中，sequential previous-anchor selector 对 102 个 wrong-selection 恢复 exact=`37`、nearby=`10`；对 182 个 nearby_target_bin_channel 恢复 exact=`17`、nearby=`45`。因此 selector/path 本身能够改变一部分频率选择结果，但它没有解决真实 target 的独立物理确认，也没有形成 20 s 与 60 s 两种窗口的同一 selector contract 对照。

结论是：当前 9.094555 bpm 的窗口差异不能被归因于窗口长度 alone。#25 保持 `WAIT_ON_SELECTOR_VALIDITY`，不按 MAE 选择或推广 60 s；下一步只有在 selector/target/bin/channel contract 可在两种窗口中一致复现时，才允许做预先冻结的 window comparison。

`REUSE_REJECTION_REASON`：已有 20 s/60 s 比较不是 canonical selector replay，已有 selector replay 也只覆盖冻结 20 s DLL-time windows；在 contract 未闭合前新增 60 s selector rerun 会把未分离的 path confound 重新包装成窗口效应，故本轮不新增窗口或算法实验。
