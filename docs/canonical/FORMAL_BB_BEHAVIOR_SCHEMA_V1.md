# Formal BB behavior schema V1

Status: reusable derived-data contract; no formal 44-session result is included. Evidence basis: `kyandi233-dev/FocusWave-Formal-Analysis@171b081f3a3f9d06496c7b8d36915eebd4e2a3bb`.

## Input contracts

The frozen session manifest has one row per session/Block/source file and requires `session_id`, `block_id`, `behavior_path`, `include`, `exclusion_reason`, and `source_contract`. `source_contract` must be `focuswave_raw_behavior_bb_v1` unless a reviewed configuration explicitly adds another raw contract. Paths containing a BBB/`050-sart-formal` component and inputs containing known derived fields are rejected.

The anonymous identity map requires one row per `session_id` with `anonymous_participant_group_id` and `identity_status`. The producer does not create identities. The example configuration explicitly excludes `sub-9504`; a frozen manifest can also mark it `include=false`. No session count or participant-group count is hardcoded.

## Standard output tables

| Table | Unique key | Analysis unit | Main contents |
|---|---|---|---|
| `trial_metrics.csv` | `trial_key` | trial | raw Go/No-Go facts, correct-Go RT, Q1/Q2 codes, opportunity flags, numerator flags, unit, calculation status, QC reason |
| `window_metrics.csv` | `window_key` | probe-preceding or fixed-second window | half-open time boundary, actual opportunities, numerators/denominators, RT family, SDT family, Q1/Q2 on probe windows |
| `phase_cycle_metrics.csv` | session + Block + type + ID | phase or cycle | the same aggregate contract at phase/cycle scale |
| `block_metrics.csv` | session + Block | Block | the same aggregate contract at Block scale |
| `session_metrics.csv` | `session_id` | acquisition session | the same aggregate contract at session scale; session is not treated as an independent natural participant |
| `error_trajectory_metrics.csv` | error event + trial offset | error-centered trial | commission/omission event type, offset, correct-Go RT availability, denominator and failure reason |

Every aggregate row keeps `total_trial_opportunities`, `go_opportunities`, `nogo_opportunities`, `correct_go_rt_opportunities`, commission/omission/accuracy/error numerators and denominators, `metric_unit`, `calculation_status`, and `qc_reason`. SDT fields additionally keep raw and log-linear-corrected hit/false-alarm rates and `sdt_status`.

## Metric definitions

- Correct-Go RT uses Go trials with `correct=1`, a present response, and configured RT bounds. The V1 example uses 150–2000 ms; the frozen run configuration is authoritative.
- RT mean, median, sample SD, median absolute deviation (MAD), interquartile range (IQR), coefficient of variation (CV), and Theil–Sen robust slope are recomputed independently at each supported scale. The slope unit is ms/s.
- Commission is No-Go response error over No-Go opportunities. Omission is missed Go over Go opportunities. Overall error is commission plus omission over all trial opportunities.
- `dprime_loglinear`, `criterion_c`, and `beta` are calculated only after configured Go and No-Go opportunity gates pass. Raw rates are retained; corrected rates use `(count + 0.5)/(opportunities + 1)`. A rejected unit remains missing with `sdt_status=rejected_low_opportunity`.
- Probe windows are `[probe_onset-window, probe_onset)`: the left boundary is included and the probe anchor is excluded. Fixed windows use the same half-open convention.
- `q1_nominal_4class` retains the four nominal Q1 codes. `q2_ordinal_4level` retains the ordered 1–4 Q2 code. They are not averaged together or converted into an unvalidated focus score.

## Compatibility with the existing 12 probe features

`window_metrics.csv` retains aliases `trial_count`, `rt_mean`, `rt_median`, `rt_sd`, `rt_mad`, `rt_cv`, `rt_slope`, `accuracy`, `error_count`, `error_rate`, `omission_count`, and `omission_rate`. These aliases make downstream migration explicit, but V1 replaces ambiguous historical semantics with correct-Go RT, an exact seconds boundary, opportunities/denominators, units, and status fields. Existing accepted 70-session canonical results are not rewritten; they remain historical analysis surfaces with their own frozen RT definitions.

`rt_cv` and `rt_slope` are not permanently assigned to one scale: the canonical V1 names `go_correct_rt_cv` and `go_correct_rt_theilsen_slope_ms_per_s` occur in window, phase/cycle, Block, and session tables whenever their scale-specific calculation gate passes.

## Participant-safe modelling boundary

`group_validation.py` builds `GroupKFold` assignments from `anonymous_participant_group_id`, asserts that no group crosses a fold, and fits imputation, scaling, and feature selection only on the training fold. It does not authorize a particular model or turn the current anonymous group keys into permanent cross-cohort identities.
