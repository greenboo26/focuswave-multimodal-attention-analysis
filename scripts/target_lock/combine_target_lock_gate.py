"""合并毫米波空间一致性摘要与RGB运动门控摘要。

输入使用subject,part_position作为键；只生成小型汇总，不读取原始视频或NPZ。
"""

import argparse
import csv
from pathlib import Path


def read(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--range-summary", required=True)
    p.add_argument("--rgb-summary", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    rgb = {(r["subject"], r["part_position"]): r for r in read(args.rgb_summary)}
    rows = []
    for r in read(args.range_summary):
        key = (r["subject"], r["part_position"])
        m = rgb.get(key, {})
        rows.append({**r, "rgb_motion_gate": m.get("motion_gate", "unavailable"),
                     "rgb_points": m.get("rgb_points", ""),
                     "dual_gate_status": "candidate_for_hr_br_review" if m.get("motion_gate") == "pass" else "hold_or_unavailable"})
    with Path(args.output).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["dual_gate_status"])
        writer.writeheader(); writer.writerows(rows)


if __name__ == "__main__":
    main()
