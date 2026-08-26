# Software and environment matrix v1

本表由实际本机环境、仓库配置和输出 manifest 交叉核对；未安装或未锁定的版本明确写为 unresolved。

| analysis family | environment | package/model evidence | backend | reproducibility state |
|---|---|---|---|---|
| behavior/questionnaire/statistics | Windows; repository `.venv` exists but lockfile absent | `requirements.txt` only; exact runtime versions not frozen | CPU expected | parameterization and version freeze still needed |
| mmWave feature extraction | Windows; root `J:\Data` and local derived outputs | scripts and manifests available; model/hash not uniformly recorded | CPU/GPU varies by script | many legacy absolute paths |
| C1b VitalSense | MATLAB R2024b Update 1, Signal Processing Toolbox R2024b; executable observed at `D:\Program Files\MATLAB\R2024b\bin\matlab.exe` | official commit `d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6` recorded in local report | CPU/MATLAB | benchmark reproducible only with external dataset mounted |
| NIR | independent `01_Attention-Analysis_nvidia-cuda`; formal output root observed | CUDA/NVIDIA candidate runs; exact model hashes and complete feature export not frozen | NVIDIA CUDA | engineering only; AMD contract not authorized |
| RGB | local output root `04_Attention-Analysis_nvidia-cuda_RGB` | frame outputs/manifests present; runner/version incomplete | CUDA candidate | engineering only |

## Required checks

```powershell
python --version
python -m pip freeze
python scripts/canonical/audit_local_analysis_library.py --repo . --derived-root D:\Project\厚粲杯\11_数据\derived --formal-nir-root D:\Project\厚粲杯\11_数据\01_Attention-Analysis_nvidia-cuda_formal_NIR --rgb-root D:\Project\厚粲杯\11_数据\04_Attention-Analysis_nvidia-cuda_RGB --j-data-root J:\Data --output work/local_library_audit.json
```

NIR/RGB 的 NVIDIA 与未来 AMD backend 只能共享 scientific contract、schema、seed、window 和 output semantics，不能把 backend 可用性当作结果等价证明。
