# Canonical entrypoints V1

## Competition execution surface

The canonical executable surface for analyses already completed locally is now:

- single stage: `python scripts/canonical/run_local_analysis.py <analysis_id> --paths configs/paths.local.json`
- competition chain: `python scripts/canonical/run_competition_pipeline.py --paths configs/paths.local.json --profile competition_core`
- machine-package collection: `python scripts/canonical/collect_machine_packages.py --paths configs/paths.local.json`
- historical-result check: `python scripts/canonical/compare_reproduction.py <analysis_id> --expected <accepted> --actual <rerun>`

The stage graph, frozen parameters, aggregate artifacts and merge-ready artifacts are defined in `configs/canonical/competition_pipeline_v1.json` and `configs/canonical/local_analysis_registry_v1.json`. Output/package naming is defined by `contracts/multimodal/MACHINE_PACKAGE_CONTRACT_V1.md` and `docs/canonical/COMPETITION_DUAL_MACHINE_RUNBOOK_V1.md`.

| entrypoint | source ref/commit | role | status |
|---|---|---|---|
| report cohort, four-class, vigilance, Probe-vigilance | `archive/20260826/report-cohort-label-vigilance` | Beijing validity family | executable canonicalization candidate |
| C+B baseline | `archive/20260826/final-report-cohort-baseline-v2` | Beijing report anchor | executable canonicalization candidate |
| questionnaire Q1 | `archive/20260826/q1-questionnaire-criterion-validity` | convergent validity | executable supporting |
| repeat-session robustness | `archive/20260826/report-repeat-session-effects` | supporting control | executable supporting |
| pre-Probe/longitudinal behavior | `archive/20260826/c1-alignment-protocol-repair` | behavior validity supplement | executable supporting |
| mmWave M1 | `archive/20260826/m1-mmwave-person-effect-audit` | raw-signal/limitation evidence | executable supporting |
| mmWave C2B-v2 | `archive/20260826/c2b-v2-canonical` | main mmWave increment test | executable canonicalization candidate |
| mmWave C2C | `archive/20260826/c2c-within-subject-normalization` | within-subject calibration | executable supporting |
| NIR local producer | external `Attention-Analysis` NVIDIA/AMD refs | standardized local NIR derived/QC | external producer; not moved into this local-analysis chain |
| RGB local producer | external rgb-nvidia/rgb-amd family | engineering derived/QC | formal analysis pending |
| fusion/cross-site | machine-package collector then central stage | combined inputs and final inference | input interface implemented; final merged inference follows combined data |

Historical scripts and task branches not listed above remain recoverable through immutable archive tags. They are not separate current execution entrypoints unless registered in `local_analysis_registry_v1.json`.
