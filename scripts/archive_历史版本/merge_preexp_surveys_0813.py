# -*- coding: utf-8 -*-
"""
merge_preexp_surveys_0813.py — 预实验事后问卷合并脚本
==================================================
文件名：merge_preexp_surveys_0813.py
版本：v1.0（2026-08-13）
功能：合并两批预实验事后问卷答卷（v3 版 3 人 + v4 版 4 人）为统一 7 人数据集。
      v3 版答卷未含实验编号题，按答卷顺序补编号 001-003；
      v4 版自带编号 005/004/006/007（非顺序排列，保留原始编号）。
      两份问卷除"实验编号"一列外题目文字完全一致（v3 题号整体 +1 偏移），
      合并后统一采用 v4 版列名（48 列）。

用法示例：
    python merge_preexp_surveys_0813.py

依赖：pandas、openpyxl（读取 xlsx）
"""

import os

import pandas as pd

# ============================================================
# 参数集中声明
# ============================================================
SURVEY_DIR = r'D:\Project\厚粲杯\05_实验\实验问卷\预实验答卷'   # 答卷目录（可改）
V3_FILE = '379204387_按文本_注意状态实验问卷_3_3.xlsx'           # v3 版答卷（3 人，无编号列）
V4_FILE = '379636869_按文本_注意状态测量实验问卷_4_4.xlsx'       # v4 版答卷（4 人，含编号列）
V3_SUBJECT_IDS = ['001', '002', '003']                          # v3 版补编号（按答卷行序）
ID_COL_INDEX = 6                                                 # v4 版编号列位置（0 起，第 7 列）
OUT_FILE = os.path.join(SURVEY_DIR, '预实验答卷_合并_001-007.csv')  # 合并输出（UTF-8-SIG，Excel 可直开）


def load_v3(id_column_name):
    """读取 v3 版答卷并补上实验编号列。

    v3 版 47 列 = 6 列元数据 + 41 列题目；v4 版 48 列 = 6 列元数据 + 编号 + 41 列题目。
    已验证 v3 列 6-46 与 v4 列 7-47 题目文字逐一相同，故在 v3 列 6 位置插入编号列即可对齐。

    Args:
        id_column_name: v4 版编号列的真实列名（含题号前缀与冒号，保持 concat 对齐）

    Returns:
        DataFrame：列结构与 v4 版一致的 v3 答卷
    """
    df = pd.read_excel(os.path.join(SURVEY_DIR, V3_FILE), header=0)
    # 按答卷行序插入编号（v3 版 3 名被试即 001-003），列名与 v4 完全一致
    df.insert(6, id_column_name, V3_SUBJECT_IDS)
    # 元数据列序号改为与 v4 一致（v4 的序号列对应答卷提交顺序，v3 保持 1-3 不变）
    df.columns = [str(c) for c in df.columns]
    return df


def load_v4():
    """读取 v4 版答卷，列名转字符串统一。

    Returns:
        DataFrame：v4 版答卷（含实验编号列）
    """
    df = pd.read_excel(os.path.join(SURVEY_DIR, V4_FILE), header=0)
    df.columns = [str(c) for c in df.columns]
    return df


def main():
    """执行合并：读取两批答卷、校验列对齐、按行拼接、落盘 CSV。"""
    df4 = load_v4()
    # v4 编号列在固定位置（第 7 列），取真实列名供 v3 插入对齐
    id_column_name = df4.columns[ID_COL_INDEX]
    df3 = load_v3(id_column_name)

    # 校验：两批列数一致且题目列（第 7 列起）文字相同
    assert len(df3.columns) == len(df4.columns), \
        f'列数不一致：v3={len(df3.columns)}, v4={len(df4.columns)}'
    for i in range(7, len(df3.columns)):
        t3 = df3.columns[i].split('、', 1)[-1]
        t4 = df4.columns[i].split('、', 1)[-1]
        assert t3 == t4, f'第 {i} 列题目不一致：v3[{t3}] vs v4[{t4}]'

    # 列名统一为 v4 版：两版题目文字一致但题号前缀不同（v3 题号整体 +1），
    # 直接按位置套用 v4 列名，避免 concat 按列名对齐时错位膨胀
    df3.columns = df4.columns

    # 按行拼接（v3 前 + v4 后），列名统一为 v4 版
    merged = pd.concat([df3, df4], axis=0, ignore_index=True)

    # 编号规范化：v3 插入的是 '001' 字符串，v4 原值为数字 4-7，统一补零为 3 位字符串
    ids = (merged[id_column_name].astype(str).str.strip()
           .apply(lambda x: str(int(float(x))).zfill(3)))
    merged[id_column_name] = ids

    # 校验编号：7 人无缺失、无重复
    assert ids.isin(['001', '002', '003', '004', '005', '006', '007']).all(), \
        f'存在未预期编号：{sorted(set(ids) - set("001 002 003 004 005 006 007".split()))}'
    assert not ids.duplicated().any(), '存在重复编号'

    merged.to_csv(OUT_FILE, index=False, encoding='utf-8-sig')
    print(f'[OK] 合并完成：{len(merged)} 人 -> {OUT_FILE}')
    print(f'     编号：{sorted(ids)}')
    print(f'     列数：{len(merged.columns)}')


if __name__ == '__main__':
    main()
