# Result reporting standard v1

Every report states `n participant / session / probe`, cohort rule, missingness and exclusions, input RUN_ID, code/config commit, output schema, and the status enum.

| result type | must report | must not omit |
|---|---|---|
| descriptive | unit, n, mean/median, dispersion, missingness | participant/session distinction |
| GEE/mixed model | formula, link, grouping, beta/OR, CI, p/q, convergence | repeated-measures handling |
| classification/CV | fold rule, AUC/balanced accuracy, CI, prevalence, threshold | participant-disjoint split and preprocessing fit scope |
| modality increment | matched cohort, baseline vs increment, delta and bootstrap CI | common-row counts and missingness |
| QC/coverage | pass/uncertain/reject counts and rules | denominator and raw-vs-derived distinction |
| cross-site | train/test site, harmonization, site-specific n, transfer metric | Beijing/Zhuhai protocol asymmetry |

No HR/BR/HRV accuracy claim is permitted from an engineering output alone; RMSSD/SDNN diagnostic values remain diagnostic until beat/IBI validation is accepted.
