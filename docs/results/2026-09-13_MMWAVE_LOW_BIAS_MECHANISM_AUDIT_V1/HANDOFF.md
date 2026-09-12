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

CLOUD_HANDOFF: 见 `CLOUD_HANDOFF_VERIFICATION.json`（本任务独立目录
`2026-09-13_mmwave_low_bias_mechanism_audit_v1`，不混入 snapshot v1 或 estimator improvement 文件）。

HR/BR: `HOLD / SUPPORTING_ONLY`

HRV: `BLOCKED`

models_trained: `false`
