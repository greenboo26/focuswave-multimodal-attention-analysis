# Output layout v1

## Observed local layout

- source code/config/docs: repository `scripts/`, `configs/`, `docs/`;
- canonical derived root on this machine: `D:\Project\厚粲杯\11_数据\derived\`;
- formal NIR output: `D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR\`;
- RGB output: `D:\Project\厚粲杯\11_数据\04_Attention-Analysis_nvidia-cuda_RGB\`;
- raw mmWave discovery: `J:\Data` and related external roots.

## Rules

New result packages use `{analysis_id}_{version}` and contain a run manifest with `RUN_ID`, code commit, config digest, input roots, schema version, seed, status and output list. Large regenerated outputs, raw row-level data, NPZ/MAT/BIN/AVI, model caches and participant identifiers stay local. Git stores scripts, configs, schemas, aggregate reports and redacted manifests.

The old repository `output/` remains historical/ignored. New canonical derived outputs are not copied into Git merely to make a status claim; the registry points to their external local path.
