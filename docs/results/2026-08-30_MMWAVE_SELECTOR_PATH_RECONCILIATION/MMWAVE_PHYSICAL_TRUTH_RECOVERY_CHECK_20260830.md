# #26 independent physical-truth recovery check — 2026-08-30

状态：`PARTIAL / PHYSICAL_GATE_UNRESOLVED / HARD_EXTERNAL_BLOCKER`

## 检查范围

本轮只读检查了 canonical project 的 existing distance/near-side evidence、实验生产仓库 `D:\Project\厚粲杯\05_实验\FocusWave` 的 README、采集程序、range verification tool、docs/changelog，以及仓库内可识别的 image/diagram assets。没有把 `selected_bin × 0.037 m`、HR error、range verification threshold 或协议文字当作 session-level physical truth。

## 找到的内容

- `D:\Project\厚粲杯\05_实验\FocusWave\README.md:105` 记录“正对被试胸骨上段，距离 0.4m”，属于实验摆位 protocol instruction，不是逐 session 的测量、照片、marker 或 geometry receipt。
- `D:\Project\厚粲杯\05_实验\FocusWave\02-tools\04b-verify-human-range.py` 使用约 `0.8m` 的现场验证目标，输出“雷达能看到人体”的工程检查；它不能证明正式采集时的胸距或被选 bright structure 的物理身份。
- 仓库中的 PNG 主要是实验刺激、界面和评分素材；本轮没有发现与 335 个 DLL-time windows 绑定的 radar-to-body measurement、摆位照片、可核验几何图或 session metadata。

## 结论

未恢复到新的独立物理真值。当前缺少的事实是：每个相关 session/block 采集时 radar face 到被试胸骨/胸廓参考面的实际距离、雷达朝向/俯仰、以及 selected/near-side bright structure 是否为人体胸廓的独立身份确认。故不能用该回放重设 distance threshold、near-side exclusion 或 physical gate；#26 正式保持 `HARD_EXTERNAL_BLOCKER / PHYSICAL_GATE_UNRESOLVED`，不再继续按误差探索阈值。

`REUSE_REJECTION_REASON`：canonical distance/error audit、protocol notes 和 range verification tool 已覆盖现有工程证据，但都不能替代 session-level independent placement truth；新增 estimator、gate 或 retrospective distance tuning 不会补足缺失的外部事实，因此本轮不新增算法或 gate。
