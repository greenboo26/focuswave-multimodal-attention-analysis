# -*- coding: utf-8 -*-
"""run_rsp_gate.py — A2 端到端驱动
对 D:\acq_mmwave_results 下某被试跑 process_vital_signs_v3_1_1.analyze_long_record,
自动从同名 .acq 提取 RSP 呼吸带呼吸率, 经 ext_br_bpm 接入毫米波侧候选频率门控
(approach ① / respiration_harmonic_reject), 解决 0816 报告的「锁半频=强而错」。

用法:
    python run_rsp_gate.py 97795
    python run_rsp_gate.py 97795 --no-acq     # 对照组: 不接 RSP 先验

输出: output/A2_rsp_gate/sub-{sub}/ 下 result.json + 图; 终端打印
      external_respiration_bpm 与 n_resp_harmonic_rejected。
"""
from __future__ import annotations
import sys
import argparse
from pathlib import Path

ROOT = Path(r"D:\acq_mmwave_results")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import process_vital_signs_v3_1_1 as algo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subject", help="被试编号, 如 97795")
    ap.add_argument("--no-acq", action="store_true", help="对照组: 不接 RSP 先验")
    args = ap.parse_args()

    sub = args.subject
    data_dir = ROOT / f"sub-{sub}_"
    acqs = list(data_dir.glob("*.acq"))
    if not acqs:
        print(f"[ERROR] 找不到 acq: {data_dir}")
        return 1
    acq_path = acqs[0]
    mm_dir = data_dir / "mmwave"
    pattern = f"sub-{sub}_mmwave_datacube_part*.npz"
    out = Path(r"D:\Project\厚粲杯\08_算法\output\A2_rsp_gate") / f"sub-{sub}"
    out.mkdir(parents=True, exist_ok=True)

    acq_arg = None if args.no_acq else acq_path
    print(f"[run] subject={sub} acq_path={acq_arg} parts={mm_dir}")
    result, _wf = algo.analyze_long_record(
        parts_dir=mm_dir,
        output_dir=out,
        session=f"sub-{sub}_ses-SART",
        pattern=pattern,
        acq_path=acq_arg,
    )
    print("=== RESULT ===")
    print("external_respiration_bpm :", result.get("external_respiration_bpm"))
    print("n_resp_harmonic_rejected:", result.get("n_resp_harmonic_rejected"))
    print("version                  :", result.get("version"))
    print(f"[saved] {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
