# Formal BB behavior producer V1

This producer rebuilds current BB behavior metrics from raw trial CSV files selected by an external frozen manifest. It never discovers a cohort by subject-number range, and it never assumes a fixed session or participant count. Every selected session must have one external `anonymous_participant_group_id`; sessions in the same group remain separate rows but share the same grouping key.

Run from the repository root:

```powershell
python -m pipelines.behavior.formal_bb.producer `
  --session-manifest D:\path\frozen_behavior_session_manifest.csv `
  --identity-map D:\path\anonymous_session_participant_mapping.csv `
  --config configs\behavior\formal_bb_v1.example.json `
  --output-dir D:\_AttentionData\derived\formal-bb-v1-smoke
```

The output directory must not already exist. The producer writes trial, probe/fixed-second window, phase/cycle, Block, session, and error-trajectory tables plus `run_manifest.json`. It does not fit scientific models or publish conclusions. Before a full local run, copy the example configuration and freeze the opportunity gates and window definitions as an input artifact; do not edit them after inspecting outcome direction.
