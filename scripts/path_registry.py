"""厚粲杯当前分析阶段的统一路径登记与检查入口。

本模块只负责路径登记，不自动扫描原始数据，也不改变任何数据文件。
正式数据移动硬盘通过 paths.local.json 或环境变量 FOCUSWAVE_FORMAL_DATA_ROOT 配置。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


ALGORITHM_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ALGORITHM_ROOT / "configs"
EXAMPLE_PATH = CONFIG_DIR / "paths.example.json"
LOCAL_PATH = CONFIG_DIR / "paths.local.json"


def load_paths() -> dict[str, Any]:
    """读取本机配置优先、示例配置兜底的路径字典。"""
    source = LOCAL_PATH if LOCAL_PATH.exists() else EXAMPLE_PATH
    data = json.loads(source.read_text(encoding="utf-8"))
    formal_override = os.environ.get("FOCUSWAVE_FORMAL_DATA_ROOT")
    if formal_override:
        data["formal_data_root"] = formal_override
    data["_config_source"] = str(source)
    return data


def check_paths(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """返回存在路径和警告信息，不对路径做创建或修复。"""
    present: list[str] = []
    warnings: list[str] = []
    for key in (
        "project_root",
        "algorithm_root",
        "project_data_root",
        "calibration_root",
        "preexperiment_root",
        "formal_data_root",
    ):
        value = data.get(key)
        if not value:
            warnings.append(f"{key}: 未配置（正式数据移动硬盘可暂为空）")
            continue
        path = Path(value)
        if path.exists():
            present.append(f"{key}: {path}")
        else:
            warnings.append(f"{key}: 路径不存在 {path}")
    return present, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="检查厚粲杯当前分析阶段路径")
    parser.add_argument("--check", action="store_true", help="检查登记路径")
    args = parser.parse_args()
    if not args.check:
        parser.print_help()
        return 0

    data = load_paths()
    present, warnings = check_paths(data)
    print(f"配置来源: {data['_config_source']}")
    for item in present:
        print(f"[OK] {item}")
    for item in warnings:
        print(f"[WARN] {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
