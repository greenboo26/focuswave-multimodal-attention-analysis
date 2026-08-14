#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名: plot_gold_validation_summary.py
版本: v1.0 (2026-08-14 补录)
功能: 基于 validate_external_gold_0814.py 输出的 gold_validation_all.json，
      绘制外部金标准验证四面板汇总图（gold_validation_summary.png）。
      · 面板1: 会话级 MAE 分布直方图
      · 面板2: quality 分层窗口级绝对误差箱线图（门控有效性证据）
      · 面板3: 窗口级雷达估计 vs ECG 金标准散点（含完美一致线/2倍频线/半频线）
      · 面板4: MAE 最好的 20 个会话
用法: python scripts/plot_gold_validation_summary.py
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
# 输出: 四面板汇总图 PNG
PNG_OUT = r'output\外部数据集\02_gold_validation\gold_validation_summary.png'
# 绘图参数
FIG_SIZE = (14, 10)        # 画布尺寸（英寸），可调
HIST_BINS = 25             # MAE 直方图分箱数，可调
DPI = 150                  # 输出分辨率，可调
TOP_N = 20                 # 面板4展示的最好会话数，可调
# quality 分层配色（high/med/low，与门控逻辑语义对应）
QUALITY_COLORS = {'high': '#2ca25f', 'med': '#feb24c', 'low': '#d95f0e'}
# 中文字体（Windows 环境）
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False


def load_validation_data(json_path):
    """读取金标准验证 JSON。

    参数:
        json_path: gold_validation_all.json 路径
    返回:
        list[dict]: 每个元素为一个会话汇总，含 mae_bpm 与 windows 列表
    """
    with open(json_path, encoding='utf-8') as f:
        return json.load(f)


def collect_window_pairs(sessions, hr_field):
    """收集所有有效窗口的 (金标准, 雷达估计) 心率对。

    参数:
        sessions: load_validation_data 返回的会话列表
        hr_field: 窗口字典中雷达心率的字段名（'traj_bpm' 或 'fused_bpm'）
    返回:
        (np.ndarray, np.ndarray): (gold_bpm 数组, radar_bpm 数组)
    """
    gold, radar = [], []
    for s in sessions:
        for w in s['windows']:
            if w.get(hr_field) and w.get('gold_bpm'):
                gold.append(w['gold_bpm'])
                radar.append(w[hr_field])
    return np.array(gold), np.array(radar)


def plot_mae_hist(ax, sessions):
    """面板1: 会话级 MAE 分布直方图，标出中位数参考线。"""
    maes = [s['mae_bpm'] for s in sessions if s['mae_bpm'] is not None]
    ax.hist(maes, bins=HIST_BINS, edgecolor='k', color='#8ab4d8')
    ax.axvline(np.median(maes), color='r', ls='--',
               label=f'中位 {np.median(maes):.1f} BPM')
    ax.set_xlabel('会话级 MAE (BPM)')
    ax.set_ylabel('会话数')
    ax.set_title(f'{len(maes)} 会话 MAE 分布（中位 {np.median(maes):.1f}）')
    ax.legend()


def plot_quality_box(ax, sessions, hr_field):
    """面板2: 按 quality 分层的窗口级绝对误差箱线图。

    高置信窗口误差应显著低于低置信窗口，这是门控有效性的直接证据。
    """
    # 按 quality 分组收集 |雷达 - 金标准| 误差
    q_err = {q: [] for q in QUALITY_COLORS}
    for s in sessions:
        for w in s['windows']:
            if w.get(hr_field) and w.get('gold_bpm'):
                q_err[str(w['quality'])].append(abs(w[hr_field] - w['gold_bpm']))
    labels = list(QUALITY_COLORS)
    bp = ax.boxplot([q_err[q] for q in labels],
                    tick_labels=['high\n(高置信)', 'med\n(中置信)', 'low\n(低置信)'],
                    patch_artist=True)
    for patch, q in zip(bp['boxes'], labels):
        patch.set_facecolor(QUALITY_COLORS[q])
        patch.set_alpha(0.7)
    # 每个箱上标注中位数
    for i, q in enumerate(labels):
        ax.text(i + 1, np.median(q_err[q]), f'{np.median(q_err[q]):.1f}',
                ha='center', va='bottom', fontsize=10)
    ax.set_ylabel('窗口级绝对误差 (BPM)')
    ax.set_title('quality 分层误差')


def plot_scatter(ax, gold, radar):
    """面板3: 窗口级估计 vs 金标准散点，叠加一致性参考线。

    2倍频线/半频线用于识别谐波锁定伪影：点落在这些线上说明算法锁在
    心率的倍频或半频而非真实基频。
    """
    ax.scatter(gold, radar, s=8, alpha=0.35, c='#4a90d9')
    lim = [min(gold.min(), radar.min()) - 5,
           max(gold.max(), radar.max()) + 5]
    ax.plot(lim, lim, 'k-', lw=1.5, label='完美一致')
    ax.plot(lim, [2 * v for v in lim], 'r--', lw=1, label='2倍频线')
    ax.plot(lim, [0.5 * v for v in lim], 'r--', lw=1, label='半频线')
    ax.set_xlabel('ECG 金标准心率 (BPM)')
    ax.set_ylabel('雷达估计心率 (BPM)')
    ax.set_title('窗口级估计 vs 金标准')
    ax.legend(fontsize=9)


def plot_best_sessions(ax, sessions):
    """面板4: MAE 最低的 TOP_N 个会话横向条形图。"""
    maes = [s['mae_bpm'] for s in sessions if s['mae_bpm'] is not None]
    idx = np.argsort(maes)[:TOP_N]
    ax.barh(range(TOP_N), np.array(maes)[idx][::-1], color='#2ca25f', alpha=0.8)
    ax.set_yticks(range(TOP_N))
    ax.set_yticklabels([f'第{i + 1}好' for i in range(TOP_N - 1, -1, -1)],
                       fontsize=8)
    ax.set_xlabel('MAE (BPM)')
    ax.set_title(f'最好的 {TOP_N} 个会话')


def main():
    """主流程: 读 JSON → 画四面板 → 保存 PNG。"""
    sessions = load_validation_data(JSON_IN)

    fig, axes = plt.subplots(2, 2, figsize=FIG_SIZE)

    # 面板1/2/4 使用会话级与窗口级 traj_bpm（轨迹算法最终输出）
    plot_mae_hist(axes[0, 0], sessions)
    plot_quality_box(axes[0, 1], sessions, hr_field='traj_bpm')
    gold, radar = collect_window_pairs(sessions, hr_field='traj_bpm')
    plot_scatter(axes[1, 0], gold, radar)
    plot_best_sessions(axes[1, 1], sessions)

    maes = [s['mae_bpm'] for s in sessions if s['mae_bpm'] is not None]
    fig.suptitle(
        f'外部金标准数据集验证汇总（多bin+HPS+轨迹, MAE 中位 {np.median(maes):.1f}）',
        fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(PNG_OUT, dpi=DPI)
    print(f'[OK] 汇总图已生成: {PNG_OUT}')


if __name__ == '__main__':
    main()
