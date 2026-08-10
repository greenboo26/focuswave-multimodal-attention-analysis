"""
hrv_nonlinear.py — HRV 非线性特征（样本熵 + 去趋势波动分析）
====================================================================
版本: v1.0 (2026-08-11)
功能: 提供 SampEn（样本熵）与 DFA（去趋势波动分析）实现, 供窗级
      HRV 特征扩展使用。非线性复杂度在走神研究中用于区分意识状态
      （如"大脑空白"与"走神"在复杂度层面可能不同）。

方法:
  SampEn(m, r) = -ln(phi_{m+1}(r) / phi_m(r)), 模板匹配率对数值
  DFA: 累积和 → 分段线性去趋势 → 均方根涨落 F(s) → log-log 斜率
      alpha1 取短尺度 (4-16), alpha2 取长尺度 (16-64, IBI 序列
      长度不足时自动缩短)

用法:
  from hrv_nonlinear import sampen, dfa
  se = sampen(ibi_ms, m=2, r=0.2*std)
  a1, a2 = dfa(ibi_ms)

依赖: numpy
"""

import numpy as np


def sampen(x: np.ndarray, m: int = 2, r: float | None = None) -> float:
    """样本熵（Sample Entropy）。

    参数:
        x: IBI 序列 (ms), 长度 >= m+1
        m: 模板长度（默认 2）
        r: 匹配容差（默认 0.2 × 标准差, Richman & Moorman 标准）
    返回:
        SampEn 值（越大 = 序列越不规则/复杂）
    """
    x = np.asarray(x, float)
    n = len(x)
    if n <= m + 1:
        return float("nan")
    if r is None:
        r = 0.2 * float(np.std(x))
    if r <= 0:
        return float("nan")

    def _phi(m_):
        # 统计长度为 m_ 的模板匹配对数（不含自匹配, Richman 定义）
        n_tpl = n - m_
        count = 0
        for i in range(n_tpl - 1):
            for j in range(i + 1, n_tpl):
                if np.max(np.abs(x[i:i + m_] - x[j:j + m_])) <= r:
                    count += 1
        return count / ((n_tpl - 1) * n_tpl / 2) if n_tpl > 1 else 0.0

    phi_m = _phi(m)
    phi_m1 = _phi(m + 1)
    if phi_m <= 0 or phi_m1 <= 0:
        return float("nan")
    return float(-np.log(phi_m1 / phi_m))


def dfa(x: np.ndarray, scale_min: int = 4, scale_max: int = 16) -> tuple[float, float]:
    """去趋势波动分析, 返回 (alpha1, alpha2)。

    alpha1（短尺度 4-16）反映短期波动相关性, 与生理调节相关;
    alpha2（长尺度, 数据允许时 16-64）反映长期结构。IBI 序列
    30-45 点时 alpha2 尺度不足, 退化为单斜率（两值相同）。

    参数:
        x: IBI 序列 (ms)
        scale_min: 最短窗长（点数）
        scale_max: 最长窗长
    返回:
        (alpha1, alpha2): log-log 回归斜率, 数据不足时返回 (nan, nan)
    """
    x = np.asarray(x, float)
    n = len(x)
    if n < 2 * scale_min:
        return float("nan"), float("nan")
    # 累积和（均值中心化）
    y = np.cumsum(x - np.mean(x))
    max_scale = n // 4
    scales = []
    s = scale_min
    while s <= min(scale_max, max_scale):
        scales.append(s)
        s = int(s * 1.5) + 1
    if len(scales) < 2:
        return float("nan"), float("nan")

    def _fluctuation(s):
        # 全段覆盖: 每段 s 点, 线性去趋势, 均方根
        n_seg = n // s
        if n_seg < 1:
            return float("nan")
        resid = []
        for k in range(n_seg):
            seg = y[k * s:(k + 1) * s]
            t = np.arange(s, dtype=float)
            # 最小二乘线性拟合
            slope, intercept = np.polyfit(t, seg, 1)
            resid.extend(seg - (slope * t + intercept))
        return np.sqrt(np.mean(np.square(resid)))

    fs = [np.log(_fluctuation(sc)) for sc in scales]
    ls = np.log(np.asarray(scales, float))
    alpha1 = float(np.polyfit(ls[:max(2, len(ls) // 2)], fs[:max(2, len(ls) // 2)], 1)[0]) \
        if len(ls) >= 2 else float("nan")
    # alpha2: 长尺度段（至少 2 点）
    if len(ls) >= 4:
        lo = len(ls) // 2
        alpha2 = float(np.polyfit(ls[lo:], fs[lo:], 1)[0]) if len(ls) - lo >= 2 else alpha1
    else:
        alpha2 = alpha1
    return alpha1, alpha2
