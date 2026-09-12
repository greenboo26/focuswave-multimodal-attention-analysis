# mmWave estimator improvement v1 handoff

RUN_ID: `mmwave_estimator_improvement_v1_20260912_r1`

STATUS: `NO_STABLE_IMPROVEMENT`

branch: `codex/mmwave-estimator-improvement-v1-20260912`

source baseline: `e4c77ceed887ea0d06f21e067914d6f8e0f8aba4`

producing commit: `PENDING_FIRST_COMMIT`

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
- uploaded files: `PENDING`
- CLOUD_UPLOAD: `PENDING`

HR/BR: `HOLD / SUPPORTING_ONLY`

HRV: `BLOCKED`

models_trained: `false`
