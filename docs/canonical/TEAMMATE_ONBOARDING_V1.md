# FocusWave teammate onboarding V1

Status: `ACTIVE / TEAMMATE_HANDOFF_ENTRYPOINT`

This is the first document a second-machine teammate or their AI agent should read. It explains what each repository is for, what software to install, what local configuration is allowed, what to do first, and what must not be changed.

## 1. Two repositories, two different jobs

### Central repository

Repository: `greenboo26/focuswave-multimodal-attention-analysis`

Use the current `main` branch. Do not use legacy `master`.

This repository owns:

- scientific definitions and frozen analysis parameters;
- canonical label semantics, windows, grouping and validation rules;
- behavior/questionnaire/mmWave canonical analysis entrypoints that have already been reviewed on the Beijing machine;
- machine-package/output contracts;
- provenance, merge keys and the central collector;
- final cross-machine / cross-site reconciliation and inference.

It is **not** a raw-data repository and it is **not** the NIR/RGB production runtime.

### Sensor production repository

Repository: `kyandi233-dev/Attention-Analysis`

This repository owns the local NIR/RGB production runtime. For the AMD NIR machine, use the project-approved `amd-DirectML` line and record the exact external Git commit used by the run. A moving branch name alone is not sufficient provenance.

The authoritative AMD NIR runtime installation entrypoints are:

- `runtime/nir-formal/INSTALL.md`
- `runtime/nir-formal/README.md`
- `runtime/nir-formal/RUNBOOK_V1.md`
- `runtime/nir-formal/requirements.txt`

If an older root-level document conflicts with the formal runtime release/install documents, treat the runtime package documents as authoritative and report the discrepancy instead of guessing.

## 2. Software to install on a fresh Windows machine

Minimum operator tools:

- Windows PowerShell;
- Git;
- Miniconda/Anaconda or another Python environment manager;
- Python 3.11 is the recommended common baseline for teammate setup.

Keep the central-analysis environment and the AMD NIR runtime environment separate.

### Central analysis environment

```powershell
git clone https://github.com/greenboo26/focuswave-multimodal-attention-analysis.git
cd focuswave-multimodal-attention-analysis
git switch main

conda create -n focuswave-central python=3.11 -y
conda activate focuswave-central
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For repository tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
```

The central environment is CPU-compatible by default. A CUDA/DirectML runtime is not required merely to inspect contracts, run behavior/questionnaire analyses, or collect machine packages.

### AMD NIR runtime environment

Follow `Attention-Analysis/runtime/nir-formal/INSTALL.md` rather than duplicating its dependency lock here. The current AMD runtime documentation uses:

- Python 3.11;
- `onnxruntime-directml` for AMD/DirectML;
- a DirectX 12 capable Windows system;
- the required `b7.onnx` and `b8.onnx` model assets under `runtime/nir-formal/models/`;
- the runtime-specific `requirements.txt`.

Do not install CUDA just because the Beijing/NVIDIA machine has CUDA. AMD and NVIDIA are different runtime backends.

## 3. Local configuration in the central repository

Never edit repository code to insert drive letters. Create the ignored local configuration instead:

```powershell
Copy-Item configs/canonical/paths.local.example.json configs/paths.local.json
```

Fill only machine-local paths and identity, for example:

```json
{
  "paths": {
    "project_root": "<local project root>",
    "raw_data_root": "<local raw data root>",
    "derived_root": "<local derived root>",
    "legacy_output_root": "<local legacy output root if present>",
    "final_output_root": "<local canonical output root>",
    "teammate_input_root": "<incoming machine packages root>",
    "combined_input_root": "<combined package root>"
  },
  "machine": {
    "machine_id": "zhuhai-amd-main",
    "site": "Zhuhai"
  },
  "analysis_input_overrides": {},
  "analysis_output_overrides": {}
}
```

`configs/paths.local.json` is private machine configuration and must not be committed.

## 4. What the teammate does first

Do **not** start by blindly running `competition_core` on Zhuhai data. The current registry was built from analyses already completed on the Beijing workstation, and some producers contain Beijing-specific cohort assumptions.

The teammate first performs a local data/protocol audit:

1. locate the actual local behavior, questionnaire and available sensor data roots;
2. enumerate formal sessions and repeated participants using existing identifiers only;
3. verify the actual behavior protocol from files/timelines instead of assuming the registration-table expectation;
4. for Zhuhai, specifically verify whether the mounted formal sessions actually exhibit the expected `BBB_3x432_30probes` structure, and record any exceptions;
5. verify probe timestamps/IDs and available master timelines;
6. record which modalities are actually available per session;
7. do not assign an exact historical FocusWave Git version to a session unless session-level commit/tag/package/hash evidence exists.

For Beijing, `BB_2x432_20probes` is already supported by the mounted behavior/timeline audit. This does not imply that all Beijing sessions were run with one exact software commit.

## 5. Then run only the applicable production/analysis work

The teammate's job is not to redesign the analysis. It is to convert their local data into the same scientific and package contract.

- Behavior/questionnaire: use the central repository's frozen definitions only after the local inputs have been mapped to the expected canonical fields. Do not force Beijing-specific expected counts onto Zhuhai.
- NIR/RGB: produce local standardized derived/QC outputs with the approved `Attention-Analysis` runtime/ref, then pass those outputs into the central contract. Do not duplicate NIR/RGB production code into the central repository.
- mmWave: run only if corresponding local mmWave inputs exist and the stage is explicitly applicable. Do not restart HRV development.
- Missing modality/stage is allowed. Never fabricate a stage merely to make the package look complete.

If a central producer is Beijing-specific and no Zhuhai adapter exists yet, stop at the standardized local derived/QC package and report the missing adapter as an integration task. Do not silently modify labels, windows, folds or feature definitions to make it run.

## 6. Required output format

Every machine uses the same package structure:

```text
<final_output_root>/
└─ focuswave_canonical_v1/
   └─ <machine_id>/
      ├─ machine_package_manifest.json
      └─ <analysis_id>/
         ├─ producer_output/
         ├─ aggregate/
         ├─ merge_ready/
         └─ stage_manifest.json
```

For the teammate this normally begins with:

```text
focuswave_canonical_v1/
└─ zhuhai-amd-main/
   └─ <analysis_id>/
      ├─ producer_output/
      ├─ aggregate/
      ├─ merge_ready/
      └─ stage_manifest.json
```

The output **format and scientific signature** must be compatible across machines. The numerical results are not expected to be identical.

Do not send only loose CSV files. Return the whole machine package/stage package with its manifest.

## 7. What is checked before two machines are combined

For each merge-ready artifact, the central collector fails closed unless the scientific signature agrees. The compatibility surface includes at least:

- `pipeline_version`;
- `producer`;
- `source_ref`;
- frozen parameter object;
- `result_unit`;
- `merge_key`;
- CSV column sequence.

The collector adds source-machine/source-site fields. It does not guess column mappings and it does not average final AUCs, p-values or coefficients.

Final pooled/site-held-out inference is rerun centrally from compatible row-level derived inputs after identity/cohort reconciliation.

## 8. Hard prohibitions

The teammate or their AI agent must not:

- use legacy `master` as the analysis base;
- change label semantics, primary windows, folds, seeds, model family or feature definitions without a new reviewed pipeline version;
- invent or infer a new identity mapping merely to satisfy a merge key;
- call labels 2/3/4 collectively `mind-wandering`;
- assign historical sessions to `v3.1.4` or any other exact software version without session-level evidence;
- average Beijing and Zhuhai final AUC/p-values/coefficients;
- commit raw data, videos, NPZ/MAT/BIN/AVI, participant-level private data, `merge_ready` row-level secure-transfer tables, model secrets, or `configs/paths.local.json` to Git;
- treat NIR/RGB engineering or partial local outputs as final cross-site inference.

## 9. First-day completion checklist

A teammate is considered correctly onboarded when all of the following are true:

- central repository cloned on `main`;
- `focuswave-central` environment installs and repository tests run or any environment exception is reported;
- `configs/paths.local.json` exists locally and is ignored by Git;
- if NIR/RGB is needed, `Attention-Analysis` is checked out at the approved backend/ref and its own install/environment check passes;
- required NIR model assets are present when NIR is run;
- local formal sessions, repeated-participant identifiers, protocol structure and modality coverage are audited;
- no Beijing-only expected count has been imposed on Zhuhai;
- the first produced stage/package follows `focuswave_canonical_v1/<machine_id>/<analysis_id>/...`;
- exact Git commits/runtime backend/config hashes are preserved in provenance.

After this checklist, follow `COMPETITION_DUAL_MACHINE_RUNBOOK_V1.md` and the relevant contracts for the actual stage execution and central handoff.
