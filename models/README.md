# 共享模型权重

本目录集中保存同事通过 `mmwave-hrv-analysis` 获取算法所需的模型权重。所有权重由 Git LFS 管理，克隆后如发现文件只有指针文本，请执行 `git lfs pull`。

| 目录 | 文件 | 用途 | 来源 |
|---|---|---|---|
| `nir/` | `nir-eye-yolo26n-best.onnx`、`nir-eye-yolo26n-best.pt` | NIR 眼部检测 | `01_Attention-Analysis_nvidia-cuda/runtime/nir-formal/models/` |
| `nir/` | `ritnet-b16-fp32.onnx` | 瞳孔/虹膜分割 | `01_Attention-Analysis_nvidia-cuda/runtime/nir-formal/models/` |
| `face/` | `yolov8n-face.onnx`、`yunet_2023mar.onnx` | RGB/NIR 人脸或眼部检测辅助 | `external/attention-pipeline-v2/models/` |
| `DeepVOG/` | `DeepVOG_weights.h5`、`DeepVOG3D_weights.h5` | 历史或备用瞳孔估计路线 | `external/attention-pipeline-v2/models/` |

训练过程权重和日志仍保留在原 NIR 工程的本地 `runs/`，不作为共享运行入口。正式分析优先使用 `nir/` 下的固定权重，并在报告中记录模型文件名和 Git 提交版本。
