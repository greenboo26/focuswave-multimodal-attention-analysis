# -*- coding: utf-8 -*-
"""5 名多源被试的被试外专注判别原型。

只用于验证特征方向和数据泄漏控制，不作为最终模型。每次留一名被试作测试，
标准化参数和逻辑回归参数只用训练被试估计。
"""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np
from scipy.special import expit

INFILE = Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821\mmwave_vs_reference_probes.csv")
OUTFILE = Path(r"D:\Project\厚粲杯\08_算法\output\ACQ_reference_20260821\prototype_attention_model.json")
FEATURES = ["hr_course_mm_bpm", "br_mm_bpm", "rmssd_mm_ms", "sdnn_mm_ms", "n_ibi_mm"]


def fit_logistic(x, y, steps=2500, lr=0.03, l2=0.01):
    # class-balanced weighted logistic regression, deterministic gradient descent
    n, p = x.shape; w = np.zeros(p + 1); z = np.c_[np.ones(n), x]
    pos = max(1, int(y.sum())); neg = max(1, n - pos)
    weights = np.where(y == 1, n/(2*pos), n/(2*neg))
    for _ in range(steps):
        pr = expit(z @ w); grad = (z.T @ (weights * (pr-y))) / n
        grad[1:] += l2*w[1:]
        w -= lr*grad
    return w


def auc(y, score):
    order=np.argsort(score); ranks=np.empty(len(score),int); ranks[order]=np.arange(1,len(score)+1)
    pos=y==1; npos=pos.sum(); nneg=(~pos).sum()
    return float((ranks[pos].sum()-npos*(npos+1)/2)/(npos*nneg)) if npos and nneg else None


def main():
    with open(INFILE,encoding="utf-8-sig",newline="") as fh: rows=list(csv.DictReader(fh))
    data=[]
    for r in rows:
        if int(r["attention"]) not in (1,2,3): continue
        try: x=[float(r[k]) for k in FEATURES]
        except (ValueError,TypeError): continue
        if not np.all(np.isfinite(x)): continue
        data.append((r["subject"],np.array(x),1 if int(r["attention"])==1 else 0))
    subjects=sorted(set(x[0] for x in data)); pred=[]
    for test_sub in subjects:
        tr=[d for d in data if d[0]!=test_sub]; te=[d for d in data if d[0]==test_sub]
        xt=np.vstack([d[1] for d in tr]); yt=np.array([d[2] for d in tr]); xv=np.vstack([d[1] for d in te]); yv=np.array([d[2] for d in te])
        mu=xt.mean(0); sd=xt.std(0); sd[sd<1e-9]=1
        w=fit_logistic((xt-mu)/sd,yt); score=expit(np.c_[np.ones(len(xv)),(xv-mu)/sd]@w); yh=(score>=.5).astype(int)
        for r,y,s in zip(te,yv,score): pred.append({"subject":test_sub,"y":int(y),"score":float(s),"pred":int(s>=.5)})
    y=np.array([r['y'] for r in pred]); yh=np.array([r['pred'] for r in pred]); sc=np.array([r['score'] for r in pred])
    tp=int(((y==1)&(yh==1)).sum()); tn=int(((y==0)&(yh==0)).sum()); fp=int(((y==0)&(yh==1)).sum()); fn=int(((y==1)&(yh==0)).sum())
    sens=tp/max(1,tp+fn); spec=tn/max(1,tn+fp)
    result={"n":len(pred),"subjects":subjects,"features":FEATURES,"label_definition":"attention=1 vs attention=2/3",
            "confusion":{"tp":tp,"tn":tn,"fp":fp,"fn":fn},"sensitivity":sens,"specificity":spec,
            "balanced_accuracy":(sens+spec)/2,"auc":auc(y,sc),"predictions":pred,
            "warning":"探索性结果；样本仅5名被试，不能代表100名最终模型性能。"}
    OUTFILE.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:result[k] for k in ('n','sensitivity','specificity','balanced_accuracy','auc')},ensure_ascii=False))


if __name__=='__main__': main()
