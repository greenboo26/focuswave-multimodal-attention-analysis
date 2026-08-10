"""
analyze_survey_physio.py — 预实验答卷 × 生理/行为的交叉分析
====================================================================
版本: v1.0 (2026-08-11)
功能: 把预实验答卷（379636869 的 004-007 四份有编号答卷 + 379204387 无编号
      3 份）的关键字段结构化, 与生理（HR/HRV 基线）/行为（误错率/RT）交叉,
      检验答卷自报（睡眠/疲劳/身体不适/策略/探针理解）是否与客观指标对应。
依据: 用户指出"被试对探针的理解与我们实际做的分析有出入", 答卷是
      检验自报-客观一致性的直接来源。

数据: 05_实验/实验问卷/预实验答卷/*.xlsx（人工录入关键字段）
      output/预实验/04_汇总产物/窗特征矩阵/window_matrix.csv
输出: output/预实验/03_跨被试/09_预实验-优化实验/SURVEY/
        survey_physio_summary.json + 控制台报告
用法:
  cd 08_算法/scripts
  python analyze_survey_physio.py
依赖: numpy
"""

import csv
import json
from pathlib import Path

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
OUT_DIR = SCRIPT_DIR.parent / "output" / "预实验" / "03_跨被试" / "09_预实验-优化实验" / "SURVEY"

# 004-007 答卷关键字段（人工从 xlsx 提取）
# 字段: sleep_h(睡眠), focus_self(自我专注力), strategy(策略), fatigue_t(疲劳时间点),
#       rest_recover(休息恢复), discomfort(身体不适), probe_understanding(探针理解),
#       comm_rate(行为误按率, 从行为 CSV 计算), rt_median
SURVEY = {
    "004": {"sleep_h": 5, "focus_self": "比较能专注", "strategy": "找规律验证",
            "fatigue_t": "每轮前期不集中", "rest_recover": "反而更难集中",
            "discomfort": "手酸(轻微)", "probe_understanding": "整个间隔(模糊)"},
    "005": {"sleep_h": 6.5, "focus_self": "比较容易走神", "strategy": "手指离键延长判断",
            "fatigue_t": None, "rest_recover": "明显恢复",
            "discomfort": "手指僵硬", "probe_understanding": "整个间隔"},
    "006": {"sleep_h": 8, "focus_self": "比较容易走神", "strategy": "计数找规律",
            "fatigue_t": None, "rest_recover": "明显恢复",
            "discomfort": "无", "probe_understanding": "前一次按键时刻"},
    "007": {"sleep_h": 8, "focus_self": "比较能专注", "strategy": "找规律(4+3间隔)",
            "fatigue_t": "后期", "rest_recover": "明显恢复",
            "discomfort": "腰酸(明显)", "probe_understanding": "整个间隔"},
}


def load_window_stats():
    """从窗特征矩阵读各被试生理/行为汇总。"""
    p = SCRIPT_DIR.parent / "output" / "预实验" / "04_汇总产物" / "09_预实验-窗特征矩阵" / "window_matrix.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    out = {}
    for sub in SURVEY:
        sr = [r for r in rows if r["subject"] == sub]
        if not sr:
            continue
        def med(f):
            v = [float(r[f]) for r in sr if r.get(f) and r[f] not in ("", "None")]
            return round(float(np.median(v)), 2) if v else None
        err = [float(r["err_rate"]) for r in sr if r.get("err_rate") not in (None, "", "None")]
        out[sub] = {"hr": med("hr_bpm"), "sdnn": med("sdnn_ms"), "rmssd": med("rmssd_ms"),
                    "sampen": med("sampen"), "rt": med("rt_mean"),
                    "err_rate": round(float(np.mean(err)), 4) if err else None,
                    "n_windows": len(sr)}
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats_ = load_window_stats()
    print("=" * 70)
    print("  预实验答卷 × 生理/行为交叉分析（004-007）")
    print("=" * 70)
    print(f"{'被试':<5}{'睡眠':<5}{'HR':<7}{'SDNN':<7}{'RMSSD':<8}{'SampEn':<8}{'RT':<7}{'误按率':<8}{'自报不适':<12}{'策略':<12}")
    for sub in ["004", "005", "006", "007"]:
        s = SURVEY[sub]
        st = stats_.get(sub, {})
        print(f"{sub:<5}{s['sleep_h']:<5}{st.get('hr','-'):<7}{st.get('sdnn','-'):<7}"
              f"{st.get('rmssd','-'):<8}{st.get('sampen','-'):<8}{st.get('rt','-'):<7}"
              f"{st.get('err_rate','-'):<8}{s['discomfort']:<12}{s['strategy'][:10]:<12}")

    # 交叉观察
    obs = []
    # 1. 睡眠 × HR 基线
    hrs = [(SURVEY[s]["sleep_h"], stats_[s].get("hr")) for s in ["004", "005", "006", "007"] if stats_[s].get("hr")]
    obs.append(f"睡眠×HR: {hrs}")
    # 2. 睡眠 × SDNN
    sd = [(SURVEY[s]["sleep_h"], stats_[s].get("sdnn")) for s in ["004", "005", "006", "007"] if stats_[s].get("sdnn")]
    obs.append(f"睡眠×SDNN: {sd}")
    # 3. 身体不适 × 误按率
    dc = [(SURVEY[s]["discomfort"], stats_[s].get("err_rate")) for s in ["004", "005", "006", "007"] if stats_[s].get("err_rate") is not None]
    obs.append(f"不适×误按率: {dc}")
    # 4. 探针理解分组（004/005/007 理解=整个间隔 vs 006=前一次按键）
    grp_interval = [stats_[s].get("err_rate") for s in ["004", "005", "007"] if stats_[s].get("err_rate") is not None]
    grp_narrow = [stats_[s].get("err_rate") for s in ["006"] if stats_[s].get("err_rate") is not None]
    obs.append(f"探针理解'整个间隔'(004/005/007)误按率 {grp_interval} vs '前一次按键'(006) {grp_narrow}")
    # 5. 自我专注力 × 行为
    fs = [(SURVEY[s]["focus_self"], stats_[s].get("err_rate")) for s in ["004", "005", "006", "007"] if stats_[s].get("err_rate") is not None]
    obs.append(f"自我专注力×误按率: {fs}")

    result = {"subjects": {s: {"survey": SURVEY[s], "stats": stats_.get(s, {})} for s in SURVEY},
              "observations": obs}
    with open(OUT_DIR / "survey_physio_summary.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\n交叉观察:")
    for o in obs:
        print(f"  - {o}")
    print(f"\n[json] {OUT_DIR / 'survey_physio_summary.json'}")


if __name__ == "__main__":
    main()
