# Beijing C+B baseline V2

Status: `CANONICAL_BEIJING_REPORT_BASELINE`; report cohort 70 sessions, 46 natural participants, 1,400 probes. Endpoint is label 1 versus labels 2/3/4. Primary window is 30 s; 10/20 s are sensitivity windows. Model is L2 logistic regression with participant-disjoint fixed 5-fold StratifiedGroupKFold, fold-local imputation/scaling/fitting, and participant-cluster bootstrap (1,000 replicates, seed 20260826).

Producer: `codex/final-report-cohort-baseline-v2@414a4f46c8d058961a87750345d06a7129afc9f2`. The 30 s C+B ROC-AUC is approximately 0.675, bootstrap 95% CI [0.621, 0.726]. Calibration is descriptive only. This Beijing fold assignment cannot be called the future global Beijing+Zhuhai fold assignment.
