#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sync the external asset audit result into the preregistration validation-set plan.

File: apply_external_audit_routing_sync_20260913.py
Version: 1.0.0
Purpose:
    把 MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1 的结论写回
    MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1：
      - 修正原计划漏掉外部数据集的 inventory 缺口；
      - 记录三个外部资产的判定；
      - 把路由固定为 OPT_A 作 primary + VS_DATASET 作 secondary C2 证据。

Usage:
    python scripts/maintenance/apply_external_audit_routing_sync_20260913.py

Dependencies:
    仅 Python 标准库。
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLAN = REPO / "docs" / "canonical" / "MMWAVE_HR_UNTOUCHED_VALIDATION_SET_PLAN_V1.md"

ANCHOR = "### 2.4 The formal cohort (the realistic untouched pool)"

SECTION = """### 2.3b External public datasets (added by `MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1`)

The original version of this plan inventoried only internal sources and therefore missed three external datasets already present on this machine. The external audit closed that gap. Result: **no external asset is usable as a primary untouched validation set, and none can serve C1 at all.**

| dataset | HR/ECG ground truth | radar input | 30 s feasible | C1 | C2 | exposure | verdict |
|---|---|---|---|---|---|---|---|
| `VS_DATASET_healthy_v1` | yes — Mindray ECG Lead II, 500 Hz, 120 s | pre-extracted single displacement channel (`VitalSig`, 40,000 @ 333.3 Hz); no DataCube | yes | **no** | yes | `DEVELOPMENT_EXPOSED` — completed C1b benchmark `C1B_VS_DATASET_20260825_V1`, 24 subjects / 48 pairs / 384 rows | `PARTIAL_CANDIDATE_SECONDARY` |
| `AgeBalanced_60GHz` | yes — Movesense ECG ~250 Hz | compressed range-FFT frames (10 Hz) | yes | no | no | `DEVELOPMENT_EXPOSED` — HR route evaluation and selection, commit `f4a8c74d89ec28e005c537cbd5280a15dcb584e1` | `INELIGIBLE_FOR_PRIMARY_VALIDATION` |
| `mmWave_Heartbeat` (TI gby) | **no** | raw ADC only | no | no | no | never run | `INELIGIBLE` |

Two consequences bind the validation design:

- **C1** can only be validated by `OPT_A`. `VS_DATASET` provides no C1 evidence at all, because C1 targets the spectral-candidate score inside the selection chain over a complex range-domain DataCube, and this dataset has no range bins, no channels and no DataCube.
- **C2** keeps `OPT_A` as its primary validation. `VS_DATASET` is added as **secondary external evidence only**, and any C2 result reported from it must state both that it is secondary and that the cohort was previously consumed by the C1b benchmark.

Frozen criteria and thresholds are unchanged; the availability of external data must not relax them.

Evidence: `docs/results/2026-09-13_MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1/`.

"""

ROUTING_ANCHOR = "**Recommendation: `OPT_A`.**"

ROUTING_NOTE = """**Routing update (after the external audit): `OPT_A` is confirmed as the primary untouched validation source, to be built next.** The external audit did not remove the need for `OPT_A`; it added `VS_DATASET_healthy_v1` as secondary C2-only external evidence and excluded the other two assets. See section 2.3b.

"""


def main() -> None:
    """Insert the external-audit section and routing note."""
    text = PLAN.read_text(encoding="utf-8")

    if "MMWAVE_EXTERNAL_VALIDATION_ASSET_AUDIT_V1" in text:
        print("skip (already present)")
        return

    if text.count(ANCHOR) != 1:
        raise SystemExit(f"section anchor count {text.count(ANCHOR)}")
    text = text.replace(ANCHOR, SECTION + ANCHOR, 1)

    if text.count(ROUTING_ANCHOR) != 1:
        raise SystemExit(f"routing anchor count {text.count(ROUTING_ANCHOR)}")
    text = text.replace(ROUTING_ANCHOR, ROUTING_NOTE + ROUTING_ANCHOR, 1)

    PLAN.write_text(text, encoding="utf-8", newline="\n")
    print("validation-set plan updated with external audit routing")


if __name__ == "__main__":
    main()
