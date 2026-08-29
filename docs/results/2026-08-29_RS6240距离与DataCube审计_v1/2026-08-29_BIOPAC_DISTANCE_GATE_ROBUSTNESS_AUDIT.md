# BIOPAC 距离 gate 稳健性补证

状态：**STILL_PARTIAL**。

本轮按原 60 s 参考窗口尝试 gate-only 成对比较。完整完成了两个 HR 代表窗口（HR 好、HR 差）；两者的 target/channel/HR course 结果未产生已确认的距离-gate翻转。BR 好/差窗口的成对数值未完成，因此不能声称 BR 对 bug 稳健，也不能把历史 99-window 的 MAE=4.5902 bpm / BR MAE=11.7689 bpm 直接升级为 corrected-gate 复现。

正式 99-window denominator 仍是历史 5-session、100 个窗口中 99 个有效；本轮 corrected-gate 可重算 denominator 只有已完成的代表窗口，禁止混称为 99-window。

判定：HR course=`STILL_PARTIAL`；BR=`STILL_PARTIAL`。不能据本轮宣布 `MATERIALLY_AFFECTED` 或 `ROBUST_TO_DISTANCE_BUG`。

正式 71 场距离 QC 已完成独立重算：保留 selected bin，不重选 target。transition 为 PASS→PASS=33、PASS→FAIL=2、FAIL→PASS=16、FAIL→FAIL=20；旧 PASS=35，新 PASS=49。canonical mainline 仍为 70-session denominator，`sub-067`、`sub-099` 原有 provenance 不变。
