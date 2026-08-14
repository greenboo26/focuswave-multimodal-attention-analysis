#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: plot_gold_methods_compare.py
版本: v1.0 (2026-08-14)
功能: 基于 gold_validation_all.json，对比时域/频域/融合/轨迹四种心率估计
      方法在金标准数据集上的验证表现，输出四面板对比图。
      · 面板1: 各方法窗口级绝对误差分布箱线图
      · 面板2: 方法 × quality 分层的 MAE 中位对比
      · 面板3: 频域估计 vs 金标准散点（含完美一致线/2倍频线/半频线）
      · 面板4: 时域估计 vs 金标准散点（同上参考线）
用法: python scripts/plot_gold_methods_compare.py
依赖: numpy, matplotlib (>= 3.9，需支持 tick_labels 参数)
数据: output/外部数据集/02_gold_validation/gold_validation_all.json
"""

import json

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ============ 集中参数声明 ============
# 输入: validate_external_gold_0814.py 的汇总结果 JSON
JSON_IN = r'output\外部数据集\02_gold_validation\gold_validation_all.json'
# 输出: 四面板方法对比图 PNG
PNG_OUT = r'output\外部数据集\02_gold_validation\methods_compare.png'
# 绘图参数
FIG_SIZE = (14, 10)        # 画布尺寸（英寸），可调
DPI = 150                  # 输出分辨率，可调
# 方法定义: (字段名, 显示名, 颜色)
METHODS = [
    ('freq_bpm',  '频域', '#4a90d9'),
    ('time_bpm',  '时域', '#d9734a'),
    ('fused_bpm', '融合', '#2ca25f'),
    ('traj_bpm',  '轨迹', '#7b5ea7'),
]
# quality 分层顺序（窗口级门控置信度）
QUALITY_ORDER = ['high', 'med', 'low']
QUALITY_NAMES = ['high\n(高置信)', 'med\n(中置信)', 'low\n(低置信)']
# 中文字体（Windows 环境）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def load_validation_data(json_path):
    """读取金标准验证 JSON。

    参数:
        json_path: gold_validation_all.json 路径
    返回:
        list[dict]: 每个元素为一个会话汇总，含 windows 列表
    """
    with open(json_path, encoding='utf-8') as f:
        return json.load(f)


def collect_errors(sessions, method_field):
    """收集某方法的窗口级绝对误差，按 quality 分组。

    参数:
        sessions: 会话汇总列表
        method_field: 方法字段名（如 'freq_bpm'）
    返回:
        dict[str, list]: {'all': 全部误差, 'high': ..., 'med': ..., 'low': ...}
    """
    errs = {'all': [], 'high': [], 'med': [], 'low': []}
    for s in sessions:
        for w in s['windows']:
            if not (w.get(method_field) and w.get('gold_bpm')):
                continue
            err = abs(w[method_field] - w['gold_bpm'])
            errs['all'].append(err)
            errs[str(w['quality'])].append(err)
    return errs


def plot_error_box(ax, sessions):
    """面板1: 各方法窗口级绝对误差箱线图（全部窗口，不筛质量）。"""
    data = [collect_errors(sessions, m)['all']
            for m, _, _ in METHODS]
    bp = ax.boxplot(data, tick_labels=[n for _, n, _ in METHODS],
                    patch_artist=True, showfliers=False)
    for patch, (_, _, c) in zip(bp['boxes'], METHODS):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    # 每个箱上标注 MAE 中位数
    for i, dd in enumerate(data):
        ax.text(i + 1, np.median(dd), f'{np.median(dd):.1f}',
                ha='center', va='bottom', fontsize=10)
    ax.set_ylabel('窗口级绝对误差 (BPM)')
    ax.set_title('各方法误差分布（全部窗口，不筛质量）')


def plot_quality_matrix(ax, sessions):
    """面板2: 方法 × quality 分层的 MAE 中位条形对比。"""
    q_colors = {'high': '#2ca25f', 'med': '#feb24c', 'low': '#d95f0e'}
    x = np.arange(len(METHODS))
    width = 0.25
    for qi, q in enumerate(QUALITY_ORDER):
        meds = []
        for m, _, _ in METHODS:
            errs = collect_errors(sessions, m)[q]
            meds.append(np.median(errs) if errs else np.nan)
        bars = ax.bar(x + (qi - 1) * width, meds, width,
                      label=QUALITY_NAMES[qi], color=q_colors[q], alpha=0.85)
        # 柱顶标注数值
        for b, v in zip(bars, meds):
            if not np.isnan(v):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f'{v:.1f}',
                        ha='center', va='bottom', fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels([n for _, n, _ in METHODS])
    ax.set_ylabel('窗口级 MAE 中位 (BPM)')
    ax.set_title('方法 × quality 分层误差（高置信窗口频域仅 0.8 BPM）')
    ax.legend(fontsize=9)


def plot_scatter(ax, sessions, method_field, title):
    """面板3/4: 某方法估计 vs 金标准散点，叠加谐波锁定参考线。

    点落在 2 倍频/半频线上说明该窗口被谐波锁定（算法锁在倍频
    而非真实基频），这是单方法误差的主要来源。
    """
    x_all, y_all = [], []
    for s in sessions:
        for w in s['windows']:
            if w.get(method_field) and w.get('gold_bpm'):
                x_all.append(w['gold_bpm'])
                y_all.append(w[method_field])
    x_all, y_all = np.array(x_all), np.array(y_all)
    ax.scatter(x_all, y_all, s=8, alpha=0.35)
    lim = [min(x_all.min(), y_all.min()) - 5,
           max(x_all.max(), y_all.max()) + 5]
    ax.plot(lim, lim, 'k-', lw=1.5, label='完美一致')
    ax.plot(lim, [2 * v for v in lim], 'r--', lw=1, label='2倍频线')
    ax.plot(lim, [0.5 * v for v in lim], 'r--', lw=1, label='半频线')
    ax.set_xlabel('ECG 金标准心率 (BPM)')
    ax.set_ylabel(f'{title}估计心率 (BPM)')
    ax.set_title(f'{title}估计 vs 金标准')
    ax.legend(fontsize=9)


def main():
    """主流程: 读 JSON → 画四面板 → 保存 PNG。"""
    sessions = load_validation_data(JSON_IN)

    fig, axes = plt.subplots(2, 2, figsize=FIG_SIZE)

    # 面板1: 各方法误差箱线图；面板2: 方法×quality 分层
    plot_error_box(axes[0, 0], sessions)
    plot_quality_matrix(axes[0, 1], sessions)
    # 面板3: 频域散点；面板4: 时域散点（对照谐波锁定现象）
    plot_scatter(axes[1, 0], sessions, 'freq_bpm', '频域')
    plot_scatter(axes[1, 1], sessions, 'time_bpm', '时域')

    fig.suptitle('时域 vs 频域方法金标准验证对比（220 会话，1188 窗口）',
                 fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(PNG_OUT, dpi=DPI)
    print(f'[OK] 对比图已生成: {PNG_OUT}')


if __name__ == '__main__':
    main()
