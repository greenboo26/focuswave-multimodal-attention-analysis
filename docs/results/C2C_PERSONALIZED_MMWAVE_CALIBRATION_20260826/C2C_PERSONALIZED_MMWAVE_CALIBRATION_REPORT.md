# C2C personal resting calibration of canonical mmWave features

状态：`WITHIN_SUBJECT_RADAR_INCREMENT_NOT_SUPPORTED`

30 s 是预冻结主分析；10/60 s 仅为冻结敏感性。C2a canonical probes、C2b-v2 行级 absolute 特征和 5-fold repeat-participant-disjoint StratifiedGroupKFold 被原样复用。每个 session 使用 experiment 前 `baseline_start` 至 `baseline_stop` 的 180 s 静息段，按分析窗切分，以 feature-wise median/MAD 构造 robust-z。

主队列：1180 probes，42 repeat participants。静息校准 session 覆盖：70/72。

| 30 s feature set | ROC-AUC [95% CI] | PR-AUC [95% CI] | Balanced accuracy [95% CI] | coverage |
|---|---|---|---|---:|
| C+B | 0.670 [0.606, 0.736] | 0.389 [0.292, 0.506] | 0.637 [0.592, 0.685] | 1.000 |
| C+B+W_absolute | 0.631 [0.573, 0.692] | 0.346 [0.254, 0.455] | 0.606 [0.560, 0.656] | 1.000 |
| C+B+W_within | 0.640 [0.568, 0.719] | 0.397 [0.288, 0.498] | 0.608 [0.552, 0.670] | 1.000 |
| W_absolute | 0.510 [0.436, 0.585] | 0.249 [0.166, 0.347] | 0.513 [0.452, 0.571] | 1.000 |
| W_within | 0.515 [0.440, 0.588] | 0.296 [0.199, 0.394] | 0.509 [0.457, 0.561] | 1.000 |

主要裁决量 ΔAUC = C+B+W_within − C+B = -0.030, participant-cluster bootstrap 95% CI [-0.083, 0.020]。

只有在主要 30 s ΔAUC 的 95% CI 完全高于 0 时才标记 supported；10/60 s 不用于选择窗口、标签或模型。行级 features、baseline statistics 和 OOF predictions 仅保留本地 derived 输出。
