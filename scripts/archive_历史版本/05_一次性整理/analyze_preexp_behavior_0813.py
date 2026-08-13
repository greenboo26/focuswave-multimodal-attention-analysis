# -*- coding: utf-8 -*-
"""
analyze_preexp_behavior_0813.py — 预实验行为数据深入分析
======================================================
文件名：analyze_preexp_behavior_0813.py
版本：v1.0（2026-08-13）
功能：读取 J 盘预实验 11 名被试的 SART 行为 CSV，计算：
      1) 每人每 Block 的 commission（no-go 虚报）率、omission（GO 漏报）率、GO RT
      2) 三条件 A/B/C 的绩效对比（SART 核心指标）
      3) 12 个 cycle 的学习曲线（验证序列规律性对绩效的影响）
      4) 探针响应分布与探针 RT
      5) 与问卷自报的对照基础表（漏按、专注自评）
      输出：J:/预实验/behavior_summary.csv（每人每 Block 一行）
            J:/预实验/behavior_cycle_summary.csv（每人每条件每 cycle 一行）
            终端打印关键汇总

用法示例：
    python analyze_preexp_behavior_0813.py

依赖：pandas
"""

import glob
import os

import pandas as pd

# ============================================================
# 参数集中声明
# ============================================================
DATA_DIR = r'J:\预实验'                          # 预实验数据根目录（可改）
SUBJECT_DIRS = sorted(glob.glob(os.path.join(DATA_DIR, 'sub-*_')))  # 被试目录列表
SUBJECT_IDS = ['001', '002', '003', '004', '005', '006', '007']     # 有问卷的 7 人
BLOCK_ORDER = ['A', 'B', 'C', 'C', 'B', 'A']                        # ABCCBA 顺序
N_CYCLES = 12                                                       # 每 Block 12 个 cycle
OUT_BLOCK = os.path.join(DATA_DIR, 'behavior_summary.csv')          # Block 级汇总输出
OUT_CYCLE = os.path.join(DATA_DIR, 'behavior_cycle_summary.csv')    # cycle 级汇总输出


def load_subject_beh(subject_dir):
    """读取单个被试全部 6 个正式 Block 的行为 CSV 并纵向拼接。

    Args:
        subject_dir: 被试目录路径（含 beh/ 子目录）

    Returns:
        DataFrame：6 Block × 216 试次拼接（练习 CSV 不读）
    """
    frames = []
    for bnum, cond in enumerate(BLOCK_ORDER, start=1):
        # 行为文件命名：sub-XXX_Block{N}_{cond}_beh.csv（目录名已含尾部下划线）
        fname = f'{os.path.basename(subject_dir)}Block{bnum}_{cond}_beh.csv'
        fpath = os.path.join(subject_dir, 'beh', fname)
        if not os.path.exists(fpath):
            print(f'  [WARN] 缺失 {fpath}')
            continue
        df = pd.read_csv(fpath, encoding='utf-8-sig')
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def block_summary(df):
    """计算单个被试单个 Block 的绩效指标。

    Args:
        df: 单 Block 行为 DataFrame（216 行）

    Returns:
        dict：commission 率、omission 率、GO RT 均值、no-go 正确率等
    """
    nogo = df[df['is_no_go'] == 1]
    go = df[df['is_no_go'] == 0]
    n_nogo = len(nogo)
    n_go = len(go)
    # commission：对 no-go 试次错误按键（虚报），SART 核心指标
    n_comm = int(nogo['commission'].sum())
    # omission：对 GO 试次漏按键（漏报）
    n_omis = int(go['omission'].sum())
    # GO 正确按键的 RT（毫秒）
    go_hit_rt = go[(go['response'] == 1)]['rt']
    return {
        'n_trials': len(df),
        'n_nogo': n_nogo,
        'n_go': n_go,
        'commission_rate': round(100.0 * n_comm / n_nogo, 2) if n_nogo else None,
        'omission_rate': round(100.0 * n_omis / n_go, 2) if n_go else None,
        'go_rt_mean': round(go_hit_rt.mean(), 1) if len(go_hit_rt) else None,
        'go_rt_median': round(go_hit_rt.median(), 1) if len(go_hit_rt) else None,
        'n_probe': int(df['is_probe'].sum()),
        'on_task_pct': round(100.0 * (df['probe_response'] == 1).sum()
                             / df['is_probe'].sum(), 1) if df['is_probe'].sum() else None,
        'probe_rt_mean': round(df['probe_rt'].mean() / 1000, 2)
                         if df['probe_rt'].notna().any() else None,
    }


def cycle_summary(df):
    """计算单个被试单个条件（2 Block 合并）内 12 个 cycle 的 no-go 正确率。

    Args:
        df: 单条件两 Block 拼接的 DataFrame（432 行）

    Returns:
        list of dict：每 cycle 一行
    """
    rows = []
    for cyc in range(1, N_CYCLES + 1):
        sub = df[df['cycle_num'] == cyc]
        nogo = sub[sub['is_no_go'] == 1]
        n_hit = int((nogo['correct'] == 1).sum()) if len(nogo) else 0
        rows.append({
            'cycle': cyc,
            'n_nogo': len(nogo),
            'nogo_correct_rate': round(100.0 * n_hit / len(nogo), 1) if len(nogo) else None,
        })
    return rows


def main():
    """主流程：逐被试读取、汇总、落盘、打印关键结果。"""
    block_rows = []   # Block 级汇总（所有被试）
    cycle_rows = []   # cycle 级汇总（仅问卷 7 人）

    for sdir in SUBJECT_DIRS:
        sid = os.path.basename(sdir).replace('sub-', '').replace('_', '')
        df_all = load_subject_beh(sdir)
        if df_all.empty:
            continue
        # Block 级汇总
        for bnum, cond in enumerate(BLOCK_ORDER, start=1):
            sub = df_all[df_all['block_num'] == bnum]
            if sub.empty:
                continue
            r = block_summary(sub)
            r.update({'subject': sid, 'block': bnum, 'condition': cond})
            block_rows.append(r)
        # cycle 级汇总（仅 7 名问卷被试，用于规律学习曲线）
        if sid in SUBJECT_IDS:
            for cond in ['A', 'B', 'C']:
                sub = df_all[df_all['condition'] == cond]
                for cr in cycle_summary(sub):
                    cr.update({'subject': sid, 'condition': cond})
                    cycle_rows.append(cr)

    df_block = pd.DataFrame(block_rows)
    df_cycle = pd.DataFrame(cycle_rows)
    df_block.to_csv(OUT_BLOCK, index=False, encoding='utf-8-sig')
    df_cycle.to_csv(OUT_CYCLE, index=False, encoding='utf-8-sig')
    print(f'[OK] Block 级汇总: {OUT_BLOCK} ({len(df_block)} 行)')
    print(f'[OK] Cycle 级汇总: {OUT_CYCLE} ({len(df_cycle)} 行)')
    print()

    # ---- 打印：每人每 Block 核心指标 ----
    print('=' * 78)
    print('每 Block 绩效（commission=no-go虚报, omission=GO漏报）')
    print('=' * 78)
    for sid in SUBJECT_IDS:
        sub = df_block[df_block['subject'] == sid]
        if sub.empty:
            continue
        parts = []
        for _, r in sub.iterrows():
            parts.append(f"{r['condition']}{r['block']}:C{r['commission_rate']:.0f}% "
                         f"O{r['omission_rate']:.0f}% RT{r['go_rt_mean']:.0f}")
        print(f"  sub-{sid}: " + ' | '.join(parts))

    # ---- 打印：条件均值对比（7 名问卷被试） ----
    print()
    print('=' * 78)
    print('条件对比（7 名问卷被试，2 Block/条件合并）')
    print('=' * 78)
    q7 = df_block[df_block['subject'].isin(SUBJECT_IDS)]
    for cond in ['A', 'B', 'C']:
        sub = q7[q7['condition'] == cond]
        print(f"  条件{cond}: commission {sub['commission_rate'].mean():.1f}% "
              f"(min {sub['commission_rate'].min():.0f} / max {sub['commission_rate'].max():.0f}), "
              f"omission {sub['omission_rate'].mean():.1f}%, "
              f"GO RT {sub['go_rt_mean'].mean():.0f}ms, "
              f"on-task {sub['on_task_pct'].mean():.0f}%")

    # ---- 打印：探针响应分布 ----
    print()
    print('=' * 78)
    print('探针响应分布（7 名问卷被试）')
    print('=' * 78)
    probe_counts = {}
    for sdir in SUBJECT_DIRS:
        sid = os.path.basename(sdir).replace('sub-', '').replace('_', '')
        if sid not in SUBJECT_IDS:
            continue
        df_all = load_subject_beh(sdir)
        resp = df_all['probe_response'].dropna().astype(int)
        probe_counts[sid] = resp.value_counts().sort_index().to_dict()
        dist = ' '.join(f'{k}:{v}' for k, v in sorted(probe_counts[sid].items()))
        on_task = 100.0 * probe_counts[sid].get(1, 0) / max(len(resp), 1)
        print(f"  sub-{sid}: {dist} | on-task {on_task:.0f}% | 探针RT均值 "
              f"{df_all['probe_rt'].mean()/1000:.1f}s")

    # ---- 打印：学习曲线（cycle 1 vs cycle 12 的 no-go 正确率） ----
    print()
    print('=' * 78)
    print('规律学习效应：cycle 1 vs cycle 12 的 no-go 正确率（%）')
    print('=' * 78)
    for sid in SUBJECT_IDS:
        sub = df_cycle[df_cycle['subject'] == sid]
        if sub.empty:
            continue
        parts = []
        for cond in ['A', 'B', 'C']:
            cc = sub[sub['condition'] == cond]
            c1 = cc[cc['cycle'] == 1]['nogo_correct_rate'].values
            c12 = cc[cc['cycle'] == 12]['nogo_correct_rate'].values
            if len(c1) and len(c12):
                parts.append(f"{cond}: {c1[0]:.0f}→{c12[0]:.0f}")
        print(f"  sub-{sid}: " + ' | '.join(parts))


if __name__ == '__main__':
    main()
