# mmWave HR untouched participant/session-disjoint ECG validation set — plan v1

Document ID: `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1`

Status: `PLANNED / SET_NOT_YET_FORMED / NO_CANDIDATE_RUN_PERMITTED`

Date: 2026-09-13 (Asia/Shanghai)

Base commit: `97cfa4e9a539d4f5df63913b24f63a1288636b6c`

This plan is the second half of the `mmwave_hr_candidate_preregistration_v1` task. It inventories which sessions/participants are already burned for HR algorithm development, identifies where a truly untouched participant/session-disjoint ECG validation set could come from, and freezes the contract that such a set must satisfy before C1/C2 may be executed.

## 1. Why a separate validation set is the binding constraint

The low-bias mechanism audit showed that the pooled `-9 bpm` is concentrated in failure classes while correct probes are nearly unbiased. That finding is only actionable if a mechanism-derived candidate can be evaluated outside the data that produced it. The current development set is:

- 5 sessions: `9779`, `97793`, `97794`, `97795`, `97796`;
- by design a **single-person repeated-measurement calibration reference** (`single_person_repeated_measurement_ecg_rsp_calibration_reference`), i.e. **not** a participant-disjoint sample;
- 100 probe windows, all with `ECG_VALID`;
- already inspected against the ECG oracle many times.

So the development set is exhausted for two independent reasons: the participant is the same across all five sessions, and the results have already been seen.

## 2. Inventory: what has been burned, and what exists

### 2.1 Sessions already used for HR development (permanently development-only)

| session | raw directory | development use |
|---|---|---|
| `9779` | `sub-9779_` | P1/P2 control, estimator improvement v1, low-bias audit |
| `97793` | `sub-97793_` | same |
| `97794` | `sub-97994_` (known alias) | same |
| `97795` | `sub-97795_` (`97995.acq`) | same |
| `97796` | `sub-97796_` | same |

### 2.2 Gold-clean per-window ECG reference currently on this machine

The only gold-clean per-window ECG/RSP reference product found is `11_数据/derived/ecg_rsp_goldclean_reaudit_v1`, whose cohort is:

- `source_windows = 100`, `sessions = 5`, `ecg_usable_windows = 100`;
- session list: `sub-97793_`, `sub-97794_`, `sub-97795_`, `sub-97796_`, `sub-9779_`.

**That is exactly the five development sessions.** No other gold-clean per-window ECG reference covering non-development sessions is present.

### 2.3 Other ECG-capable local sources (from the existing physiology reference audit)

`11_数据/derived/physiology_reference_v1/physiology_reference_session_audit.csv` describes the other locally available ECG-bearing sessions:

| session | ECG | current mmWave pair | usable as validation? |
|---|---|---|---|
| `sub-2_` | 22/22 HR windows valid | none | NO — calibration session, RSP channel absent, no probe-window pairing |
| `sub-3_` | 13/13 valid | none | NO — needs pairing/window definition before any claim |
| `sub-4_` | 15/15 valid | none | NO — same; start-marker completeness unverified |
| `sub-5_` | 13/13 valid | none | NO — same |
| `sub-6_` | not represented | none | NO — no existing clean-reference output |
| `sub-7_` | existing output only | none | NO — raw source path absent, not reusable |
| `sub-97792_` | 4/4 valid | none | NO — only four windows, insufficient |

These are calibration sessions anchored on `cal/events.csv calibration_start`; they are **not** probe-window sessions, so they cannot evaluate probe-window HR accuracy without first defining a probe-window contract that does not currently exist for them.

### 2.4 The formal cohort (the realistic untouched pool)

The governed integration-snapshot cohort is a different, much larger population:

| property | value |
|---|---|
| sessions | `116` |
| participant groups | `61` |
| repeat-participant ids | `62` |
| probes | `2,320` (20 per session) |
| session id form | `sub-031`, `sub-032`, … (numeric formal ids) |
| estimable sessions / probes | `109` / `2,180` |
| session overlap with the 5 development sessions | **`0`** (verified by set intersection) |
| participant-group overlap with the development participant | **none identified** (formal ids are a different id space) |

So a **session-disjoint** pool plainly exists at the cohort level. The blocker is not the cohort; it is that **the formal cohort's per-window gold-clean ECG reference does not exist yet** in a form comparable to the development reference.

## 3. Verification-set contract (frozen)

A candidate validation set may only be labelled `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` when **all** of the following hold. Each item must be machine-checkable and recorded in the set's manifest.

| id | requirement |
|---|---|
| `VS_1_SESSION_DISJOINT` | No session id in the set equals or aliases any of `9779`, `97793`, `97794`/`97994`, `97795`, `97796`. |
| `VS_2_PARTICIPANT_DISJOINT` | No participant group in the set is the development participant, and no participant group appears in more than one of the set's sessions **unless the set is deliberately a longitudinal subset and is labelled as such**. |
| `VS_3_UNTOUCHED` | No probe in the set has ever been used for HR algorithm development, oracle inspection, mechanism diagnosis, or candidate selection. This must be asserted for the whole set, not per probe. |
| `VS_4_INDEPENDENT_ECG_REFERENCE` | A per-window gold-clean ECG reference is generated **independently** for the set, using the identical cleaning rules as the development reference (`0.5–40 Hz` bandpass, `300–2000 ms` IBI range, adjacent IBI relative change `>20%` removed, `>=80%` normal intervals usable). The reference must not reuse development cleaning outputs. |
| `VS_5_WINDOW_CONTRACT` | Window contract identical to development: `[window_effective_start_unix_ms, probe_onset_unix_ms)`, nominal 30 s, block-truncated, no cross-block, DLL host receive/enqueue timestamp as the frame clock. |
| `VS_6_ECG_ELIGIBILITY` | Per-probe ECG eligibility is computed and reported as valid / invalid / unresolved; only `ECG_VALID` probes enter the primary denominator, and the invalid/unresolved counts are reported alongside. |
| `VS_7_DENOMINATOR_FROZEN` | Session count, participant-group count and probe count are frozen in the manifest **before** any candidate is evaluated. |
| `VS_8_NO_REUSE` | Once any candidate has been evaluated on the set, the set is consumed and may not be reused for a different candidate. |
| `VS_9_NO_DEVELOPMENT_LEAKAGE` | The set's sessions are not used at any point during candidate implementation, variant selection, or debugging. |
| `VS_10_NO_SNAPSHOT_V2` | Membership in this set does not by itself authorize any snapshot v2 or any change to snapshot v1. |

A set failing any requirement is `NOT_A_VALIDATION_SET` and may be used for descriptive work only, never for candidate success/failure.

## 4. Candidate set options, with explicit tradeoffs

| option | source | disjointness | readiness | cost / risk |
|---|---|---|---|---|
| `OPT_A` | formal cohort sessions from the 116-session snapshot, excluding nothing (no overlap exists) | session-disjoint `YES`; participant-disjoint `YES` by id space | **blocked on ECG reference** | requires a per-window gold-clean ECG run plus BIOPAC marker alignment for formal sessions; medium–high effort; must confirm raw ECG availability |
| `OPT_B` | calibration sessions `sub-3_`, `sub-4_`, `sub-5_` | session-disjoint `YES`; participant groups are separate people | **blocked on window contract** | these are calibration sessions without probe windows; would require defining and freezing a new window contract, which changes the target of validation; higher methodological risk |
| `OPT_C` | `sub-97792_` | session-disjoint `YES` | **insufficient** | only 4 ECG-valid windows; cannot support the 5 success criteria |
| `OPT_D` | new acquisition of participant/session-disjoint sessions with probe windows | ideal | **not available now** | requires new data collection; out of scope for this task |

**Recommendation: `OPT_A`.** It is the only option that is simultaneously session-disjoint, participant-disjoint, probe-window based, and large enough (109 estimable sessions / 2,180 probes available; a subset can be frozen). Its single blocker is the missing independent gold-clean ECG reference, which is a data-engineering task, not a science decision.

`OPT_B` is explicitly **not** recommended: changing the window contract to fit the available data would weaken exactly the comparability that makes the validation meaningful.

## 5. Construction steps for `OPT_A` (to be executed in a separate task)

1. **Confirm raw ECG availability** for the candidate formal sessions (BIOPAC/ECG channel present, `.acq` readable, markers decodable). Record per session; exclude any session failing this.
2. **Freeze the candidate session list** before looking at any HR accuracy: list sessions, participant groups, and probe counts into the set manifest. Do not select sessions by observed HR error.
3. **Generate the independent per-window gold-clean ECG reference** for those sessions using `scripts/gold_standard_qa.py` with the development-identical rules; record script hash, commit, and per-probe eligibility.
4. **Apply the frozen window contract** (`VS_5`) and record `ECG_VALID/INVALID/UNRESOLVED` per probe.
5. **Run the contract checks** `VS_1`–`VS_10` mechanically; any failure stops the task as `VALIDATION_SET_CONTRACT_FAILED`.
6. **Publish** `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` with manifest (sessions, participant groups, probes, per-probe eligibility, reference hashes, code commit) and `HANDOFF.md`.
7. **Do not evaluate any candidate** in the same task that builds the set. Building and first-use must be separate tasks so the set is genuinely untouched when first consumed.

## 6. Sequencing and gates

```
low-bias mechanism audit v1            DONE   (MULTIFACTOR_MECHANISM_SUPPORTED)
        |
candidate preregistration v1           DONE   (this task; C1/C2 frozen, nothing implemented)
        |
untouched ECG validation set v1        NEXT   (OPT_A construction; separate task)
        |
evaluate ONLY the preregistered C1/C2  GATED  (requires VS_1..VS_10 all pass)
        |
   pass -> snapshot v2 discussion (still a separate task and decision)
   fail -> keep MMWAVE_INTEGRATION_SNAPSHOT_V1, record negative result
```

Hard gate: **C1/C2 must not be implemented-and-evaluated before `MMWAVE_HR_UNTOUCHED_VALIDATION_SET_V1` passes its contract**, because implementing against the development set is exactly the failure mode this preregistration exists to prevent.

## 7. Boundaries

This plan:

- does not create the validation set;
- does not run any candidate;
- does not modify snapshot v1, the formal producer, the feature registry, or Task B/materialize identity;
- does not authorize snapshot v2;
- keeps HR/BR `PROVISIONAL / SUPPORTING / PHYSIOLOGY_LIMITED` and HRV `BLOCKED`;
- does not block Behavior / NIR / RGB or formal multimodal analysis — mmWave is a parallel, controlled-validation line.

## 8. Pointers

- Preregistration: `docs/canonical/MMWAVE_HR_CANDIDATE_PREREGISTRATION_V1.md`
- Criteria register: `docs/canonical/CANDIDATE_SUCCESS_CRITERIA_V1.csv`
- Formal cohort: `docs/results/2026-09-12_MMWAVE_INTEGRATION_SNAPSHOT_V1/` (116 sessions / 61 participant groups / 2,320 probes)
- Development reference cohort evidence: `11_数据/derived/ecg_rsp_goldclean_reaudit_v1/goldclean_reference_summary.json` (local-only)
- Local ECG-source audit: `11_数据/derived/physiology_reference_v1/physiology_reference_session_audit.csv` (local-only)
- Issue: #35
