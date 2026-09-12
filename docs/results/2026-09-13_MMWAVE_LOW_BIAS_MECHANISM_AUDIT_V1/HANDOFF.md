# mmWave low-bias mechanism audit v1 — handoff

RUN_ID: `mmwave_low_bias_mechanism_audit_v1_20260913_r1`

STATUS: `MULTIFACTOR_MECHANISM_SUPPORTED`

TASK_BRANCH: `codex/mmwave-low-bias-mechanism-audit-v1-20260913`

BASE_MAIN_SHA: `291e50ab4313685b0645210756c9921ec9e8f245`

objective: 解释融合心率约 −9 bpm 系统性低估的主要来源，并给出有机制依据、可预注册的
下一轮方向；不搜索 estimator rule、不形成 snapshot v2。

denominator: 5 sessions（9779, 97793, 97794, 97795, 97796）× 100 probes，
ECG_VALID 100/100，窗口 `[window_effective_start, probe_onset)` nominal 30 s，
DLL host receive/enqueue 时间源。输入三份 CSV 的 SHA-256 全部 exact match。

key result:
- `CONTROL_REPRODUCTION=PASS`（fused MAE 10.457079 / bias −9.033106 / p90 AE 24.054346；
  time MAE 8.996966 / bias −6.737621；spectral MAE 15.123834 / bias −13.351010）。
- 正确类几乎无偏：`CORRECT_OR_NEAR_CORRECT` fused bias
  0.215472 bpm。
- pooled 低估由三个失败类别承担；频域路偏得最重，融合净叠加约
  1.460 bpm 且制造
  4 个"可接受→灾难"转换。
- 距离只有弱关联且被 session/类别混淆；既有 QC 字段无 session 一致关系；
  无 ≈0.5/≈2.0 谐波锁定，但非谐波残留仍为负偏。

decision: `MULTIFACTOR_MECHANISM_SUPPORTED`。不改 producer、不改 snapshot v1、不发布 v2、
不训练模型，HRV 继续 `BLOCKED`。

code entrypoint: `scripts/maintenance/run_mmwave_low_bias_mechanism_audit_20260913.py`
（deterministic；文档由 `scripts/maintenance/render_mmwave_mechanism_audit_docs_20260913.py` 渲染）。

LOCAL_OUTPUTS:

- `D:\Project\厚粲杯\11_数据\derived\mmwave_low_bias_mechanism_audit_v1_20260913\PROBE_LEVEL_MECHANISM_100_PROBES.csv` — 100 rows — SHA-256 `76EABD8B114D7769E47508C7EC66BEE4370A658C353014A056C7AECDAF8F5BD5` — local-only，因为含逐 probe ECG 参照与诊断细节。

CLOUD_HANDOFF:

- target folder: `_AI_HANDOFF/2026-09-13_mmwave_low_bias_mechanism_audit_v1`（本任务独立目录，未混入 snapshot v1 或 estimator improvement 文件）
- transport: rclone 1.75.1（便携版，仓库外 `D:\Project\.tools\rclone.exe`），既有已授权 Google Drive remote `gdrive`；凭据只存在于本机 rclone 配置，未打印、未入日志、未入库
- uploaded files: 15（14 个 Git-safe 交付物 + `CLOUD_HANDOFF_VERIFICATION.json`）
- CLOUD_UPLOAD: `UPLOADED_AND_VERIFIED`
- verification: `rclone check --checksum` exit 0；随后把整目录回读到本机 staging 并逐文件重算 SHA-256，14/14 与本地一致，目录内不含任何 snapshot v1 / estimator improvement 文件
- `CLOUD_HANDOFF_VERIFICATION.json` SHA-256: `0DAB2E3483A1958787352DADBD3AD5A7E58653846A7CF9A6ED10D9FCD4F29FA9`（该文件最后写入，无法收录自身摘要，故记于本 handoff 与 GitHub issue pointer）
- local-only: `PROBE_LEVEL_MECHANISM_100_PROBES.csv` 未上传、未入 Git；摘要记录在审计 manifest

HR/BR: `HOLD / SUPPORTING_ONLY`

HRV: `BLOCKED`

models_trained: `false`
