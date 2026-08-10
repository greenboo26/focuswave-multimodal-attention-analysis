"""
rename_preexp_subject.py — 预实验被试编号修正工具
====================================================================
版本: v1.0 (2026-08-10)
功能: 修正采集时被试编号输入错误的文件夹数据（如 005 被试被输入为 004）:
      1) 重命名 mmwave/beh/nir/rgb 下所有含错误编号的文件
      2) 修正 mmwave/meta.json 内部 subject_id 与 bin_file/ts_file 引用
      3) 修正 CSV 内部 subject_id 数据列与 master_timeline 的 subject= 字段

用法:
  python rename_preexp_subject.py --subject 005 --wrong-id 004 --data-root F:/预实验

依赖: 无（标准库）
"""

import argparse
import json
import os
from pathlib import Path


def rename_files(sub_dir: Path, wrong: str, right: str) -> int:
    """重命名目录内所有含错误编号的文件。

    参数:
        sub_dir: sub-XXX_ 目录
        wrong: 错误编号（如 004）
        right: 正确编号（如 005）
    返回:
        重命名文件数
    """
    n = 0
    for dirpath, _, filenames in os.walk(sub_dir):
        for fn in filenames:
            new = (fn.replace(f"sub-{wrong}_", f"sub-{right}_")
                     .replace(f"SART_{wrong}", f"SART_{right}"))
            if new != fn:
                src, dst = os.path.join(dirpath, fn), os.path.join(dirpath, new)
                os.rename(src, dst)
                n += 1
    return n


def fix_meta(sub_dir: Path, subject: str, wrong: str, right: str) -> None:
    """修正 meta.json 的 subject_id 与文件引用。"""
    meta_path = sub_dir / "mmwave" / f"sub-{subject}_mmwave.meta.json"
    if not meta_path.exists():
        return
    d = json.loads(meta_path.read_text(encoding="utf-8"))
    d["subject_id"] = right
    d["bin_file"] = d["bin_file"].replace(f"sub-{wrong}_", f"sub-{right}_")
    d["ts_file"] = d["ts_file"].replace(f"sub-{wrong}_", f"sub-{right}_")
    meta_path.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    print(f"  meta.json: subject_id={d['subject_id']}, "
          f"bin_file={d['bin_file']}, ts_file={d['ts_file']}")


def fix_csv_fields(sub_dir: Path, wrong: str, right: str) -> int:
    """修正 CSV 内部 subject_id 列（行首 wrong,）与 subject=wrong 字段。

    参数:
        sub_dir: sub-XXX_ 目录
        wrong: 错误编号
        right: 正确编号
    返回:
        修改文件数
    """
    n = 0
    for dirpath, _, filenames in os.walk(sub_dir):
        for fn in filenames:
            if not fn.endswith(".csv"):
                continue
            p = Path(dirpath) / fn
            lines = p.read_text(encoding="utf-8-sig").splitlines(keepends=True)
            changed = False
            for i, line in enumerate(lines):
                if line.startswith(f"{wrong},"):
                    lines[i] = f"{right}," + line[len(wrong) + 1:]
                    changed = True
                if f"subject={wrong}" in line:
                    lines[i] = line.replace(f"subject={wrong}", f"subject={right}")
                    changed = True
            if changed:
                p.write_text("".join(lines), encoding="utf-8-sig", newline="")
                n += 1
    return n


def main():
    parser = argparse.ArgumentParser(description="预实验被试编号修正工具")
    parser.add_argument("--subject", type=str, default="005", help="正确被试编号（3 位）")
    parser.add_argument("--wrong-id", type=str, default="004", help="被误输入的编号")
    parser.add_argument("--data-root", type=str, default="F:/预实验",
                        help="数据根目录, 含 sub-XXX_/ 子目录")
    args = parser.parse_args()

    right = args.subject.zfill(3)
    wrong = args.wrong_id.zfill(3)
    sub_dir = Path(args.data_root) / f"sub-{right}_"
    if not sub_dir.exists():
        raise FileNotFoundError(f"{sub_dir} 不存在（文件夹名应为正确编号 sub-{right}_）")

    n = rename_files(sub_dir, wrong, right)
    print(f"[1/3] 重命名 {n} 个文件（sub-{wrong}_ → sub-{right}_）")
    fix_meta(sub_dir, right, wrong, right)
    print("[2/3] meta.json 已修正")
    n = fix_csv_fields(sub_dir, wrong, right)
    print(f"[3/3] CSV 内部字段修正 {n} 个文件")
    print("完成")


if __name__ == "__main__":
    main()
