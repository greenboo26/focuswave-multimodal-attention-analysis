"""Record which user-specified data, protocol, application and literature sources are covered."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def resolve_acq_root() -> Path:
    configured = os.environ.get("ACQ_SOURCE_ROOT")
    candidates = ([Path(configured)] if configured else []) + [
        Path(r"D:\acq_mmwave_results"),
        Path(r"D:\acq\_mmwave\_results"),
    ]
    return next((p for p in candidates if p.exists()), candidates[0])


def inspect(path: Path, role: str, evidence: list[str], patterns: tuple[str, ...] = ()) -> dict:
    exists = path.exists()
    files = []
    if exists and path.is_dir():
        for pattern in patterns:
            files.extend(path.rglob(pattern))
    return {
        "path": str(path),
        "exists": exists,
        "role": role,
        "file_counts": {pattern: sum(1 for f in files if f.match(pattern)) for pattern in patterns},
        "used_evidence": evidence,
    }


def main() -> None:
    sources = [
        inspect(Path(r"E:\Data"), "主行为/毫米波实验数据", [
            "行为时间戳门控、毫米波生命体征、RGB/NIR 跨模态特征、跨被试和个体化审计",
        ], ("*.csv", "*.npz", "*.avi")),
        inspect(Path(r"D:\正式实验"), "正式实验第一批行为与毫米波数据", [
            "正式实验行为探针、master_timeline、毫米波与 RGB/NIR；无 ECG/RSP，因此不作为生理金标准",
        ], ("*.csv", "*.npz", "*.avi")),
        inspect(resolve_acq_root(), "ECG/RSP/毫米波同步参照数据", [
            "BIOPAC ECG/RSP 解析、严格行为时间窗、HR/BR/HRV 独立参照验证",
        ], ("*.acq", "*.csv", "*.npz")),
        inspect(Path(r"D:\Project\厚粲杯\05_实验\FocusWave"), "实验程序包与数据格式说明", [
            "实验流程、行为标签含义、采集时钟和文件格式解释",
        ], ("*.py", "*.md", "*.json", "*.csv")),
        inspect(Path(r"D:\Project\厚粲杯\11_数据"), "外部数据集与零散数据", [
            "AgeBalanced ECG/毫米波生命体征外部审计、旧批次和校准资料，用于生理算法边界核对",
        ], ("*.csv", "*.npz", "*.json", "*.md")),
        inspect(Path(r"D:\Project\厚粲杯\03_文献"), "项目文献与方法资料", [
            "毫米波生命体征、mmHRV、专注/走神任务和方法边界的证据整理",
        ], ("*.md", "*.pdf", "*.docx")),
        inspect(Path(r"D:\Project\厚粲杯\06_申请书\南部赛区_北京师范大学珠海校区_测验赛道_咪咕咩哞呼噜噜.docx"), "项目申请书", [
            "核对项目目标、SART 行为探针、毫米波生理指标、RGB/NIR 辅助和效标验证路线",
        ]),
    ]
    result = {
        "sources": sources,
        "algorithm_outputs": [
            "output/E_Data_FAST/crossmodal_time_gate.json",
            "output/E_Data_FAST/personalized_scores_validated_behavior.json",
            "output/ACQ_reference_20260821/ACQ_reference_validation_20260822.md",
            "output/ACQ_reference_20260821/ACQ_signal_quality_audit_20260822.md",
            "output/系统验证报告_20260821.md",
        ],
        "web_method_references": [
            {"topic": "HRV short-term standards", "url": "https://www.jacc.org/doi/10.1016/j.jacc.2006.09.020"},
            {"topic": "HRV experiment planning", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/"},
            {"topic": "normal adult resting vital signs", "url": "https://medlineplus.gov/ency/article/002341.htm"},
            {"topic": "normal adult resting heart rate", "url": "https://www.heart.org/en/healthy-living/exercise-and-physical-activity/fitness-basics/target-heart-rates"},
        ],
        "boundary": "Source coverage does not make protocols homogeneous; only the E_Data layer is the main behavior cohort, ACQ is an independent physiology reference layer, and formal/other layers require harmonization before pooling.",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "source_evidence_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sources": len(sources), "missing": [s["path"] for s in sources if not s["exists"]]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
