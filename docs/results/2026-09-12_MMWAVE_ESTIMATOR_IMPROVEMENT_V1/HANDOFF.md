# mmWave estimator improvement v1 handoff

RUN_ID: `mmwave_estimator_improvement_v1_20260912_r1`

STATUS: `NO_STABLE_IMPROVEMENT`

branch: `codex/mmwave-estimator-improvement-v1-20260912`

source baseline: `e4c77ceed887ea0d06f21e067914d6f8e0f8aba4`

producing commit: `737a359bb29b1c05b83f7fbcb4a8134922f95220` (`audit(mmwave): record estimator improvement negative result`; parent `e4c77ceed887ea0d06f21e067914d6f8e0f8aba4`)

report commit: the commit that adds this producing-commit pointer; its own hash is recorded in the GitHub issue pointer because a file cannot contain its own commit hash.

objective: reconcile exact current reference/QC lineage, re-confirm P2, and test bounded mmWave-only estimator/fusion repairs without modifying integration snapshot v1.

input data: existing exact 100-key gold-clean ECG/RSP reference plus strict-reference P2 replay; 5 sessions, 100 probe windows, DLL host receive/enqueue time, nominal pre-probe 30 s, no cross-block.

code entrypoint: `scripts/maintenance/run_mmwave_estimator_improvement_v1_20260912.py`

key result: Phase A ECG valid/invalid/unresolved=`100/0/0`; RSP basic/strict=`95/79`. Observed-best but rejected H1 fused MAE=`9.618844 bpm` versus current fused=`10.457079`, current time=`8.996966`, current spectral=`15.123834`; paired improve/worsen/tie=`8/1/91`.

decision: H1/H3 introduce a new `AE>10 bpm` failure from a control-correct window; H2 does not improve at least 3/5 sessions. All three are rejected. `BEST_CANDIDATE=NONE`; `V2_CANDIDATE_STATUS=NOT_FORMED`. All five sessions were previously oracle-inspected and no untouched participant/session-disjoint ECG validation exists. Snapshot v1 and the formal producer remain unchanged.

LOCAL_OUTPUTS:

- `D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_improvement_v1_20260912_r1\final_r6\REFERENCE_QC_ELIGIBILITY_100_PROBES_LOCAL_ONLY.csv` — 100 rows — SHA-256 `EA9DB07FB37A2027569714B3193FC49AAFECA7C59690750BFFAF523C7188F479` — local-only because it contains probe-level reference/QC detail.
- `D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_improvement_v1_20260912_r1\final_r6\CONTROL_VS_CANDIDATES_100_PROBES_LOCAL_ONLY.csv` — 100 rows — SHA-256 `B4251445B1938DF61F07EFECE9ECBA4DD29FEFFCEED699E0B5B5226D0571A76D` — local-only because it contains probe-level paired estimates.
- `D:\Project\厚粲杯\11_数据\derived\mmwave_estimator_improvement_v1_20260912_r1\final_r6\LARGEST_ERROR_PROBES_TOP20_LOCAL_ONLY.csv` — 20 rows — SHA-256 `A6DE5A62434A673FD3EA976AC786962F1B8D475B284C69898C6F9FD21DEEAC49` — local-only because it identifies individual probe windows.
- A preliminary output directory created before the catastrophic-failure gate was added is marked `REJECTED_PRELIMINARY_OUTPUT_DO_NOT_USE.md`; it is superseded diagnostic residue, not a candidate and not canonical output.

CLOUD_HANDOFF:

- target folder: `2026-09-12_mmwave_estimator_improvement_v1`
- folder id: `1gZC80XNklehALcuJ6U8NJe_aKy5iwzPd`
- uploaded files: `NONE — CLOUD_UPLOAD_BLOCKED_NO_DRIVE_CONNECTOR_IN_EXECUTION_ENVIRONMENT`
- CLOUD_UPLOAD: `BLOCKED`
- blocker: the execution environment for this run exposes no Google Drive connector/MCP tool and no Drive OAuth credential; the Codex connector route (`mcp__codex_apps__google_drive_*`) is only available inside the Codex/ChatGPT app session, and the Codex CLI route returned `usage limit` at 2026-09-13T03:06 (Asia/Shanghai). Upload and read-back must therefore be executed from a session with the Google Drive connector before the task is reported as complete.
- upload manifest (exact files staged for upload): see `MMWAVE_ESTIMATOR_IMPROVEMENT_V1_MANIFEST.json` → `cloud_handoff`.

HR/BR: `HOLD / SUPPORTING_ONLY`

HRV: `BLOCKED`

models_trained: `false`
