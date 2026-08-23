"""Create a requirement-level completion audit without overstating evidence."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"D:\Project\厚粲杯\08_算法")
OUT = ROOT / "output" / "E_Data_FAST"


def main():
    summary = json.loads((OUT / "final_summary.json").read_text(encoding="utf-8"))
    lopo = summary["leave_one_subject_out"]
    target = json.loads((OUT / "target_100_audit.json").read_text(encoding="utf-8"))["summary"]
    gating = json.loads((ROOT / "output" / "ACQ_reference_20260821" / "hrv_gating_evaluation.json").read_text(encoding="utf-8"))
    ext = json.loads((ROOT / "output" / "External_AgeBalanced" / "summary.json").read_text(encoding="utf-8"))
    release = json.loads((OUT / "release_verification.json").read_text(encoding="utf-8"))
    crossmodal = json.loads((OUT / "crossmodal_time_gate.json").read_text(encoding="utf-8"))
    fusion = json.loads((OUT / "mmwave_behavior_fusion_lopo.json").read_text(encoding="utf-8"))
    visual_fusion = json.loads((OUT / "crossmodal_fusion_lopo.json").read_text(encoding="utf-8"))
    visual_within = json.loads((OUT / "crossmodal_within_subject_lopo.json").read_text(encoding="utf-8"))
    behavior_supervised = json.loads((OUT / "behavior_supervised_lopo.json").read_text(encoding="utf-8"))
    temporal_runtime = json.loads((OUT / "personalized_temporal_runtime.json").read_text(encoding="utf-8"))
    augmented = json.loads((OUT / "augmented_vitals_lopo.json").read_text(encoding="utf-8"))
    expanded_runtime = json.loads((OUT / "personalized_temporal_runtime_expanded.json").read_text(encoding="utf-8"))
    behavior_runtime = json.loads((OUT / "personalized_temporal_runtime_behavior.json").read_text(encoding="utf-8"))
    exported_runtime = json.loads((OUT / "personalized_scores_validated_behavior.json").read_text(encoding="utf-8"))
    mmwave_exported = json.loads((OUT / "personalized_scores_mmwave.json").read_text(encoding="utf-8"))
    mmwave_visual_exported = json.loads((OUT / "personalized_scores_mmwave_rgb_nir.json").read_text(encoding="utf-8"))
    breath_path = ROOT / "output" / "ACQ_reference_20260821" / "breath_method_comparison_current.json"
    if not breath_path.exists():
        breath_path = ROOT / "output" / "ACQ_reference_20260821" / "breath_method_comparison.json"
    breath_reference = json.loads(breath_path.read_text(encoding="utf-8"))
    acq_validation = json.loads((ROOT / "output" / "ACQ_reference_20260821" / "acq_reference_validation_summary.json").read_text(encoding="utf-8"))
    signal_quality = json.loads((ROOT / "output" / "ACQ_reference_20260821" / "acq_signal_quality_audit.json").read_text(encoding="utf-8"))
    source_evidence = json.loads((OUT / "source_evidence_audit.json").read_text(encoding="utf-8"))
    enhanced_visual_path = OUT / "augmented_vitals_enhanced_visual_lopo.json"
    enhanced_visual = json.loads(enhanced_visual_path.read_text(encoding="utf-8")) if enhanced_visual_path.exists() else None
    requirements = [
        {"id": "pipeline", "status": "achieved", "claim": "可复现批处理、质量门控、运行时原型和发布检查已建立", "evidence": "scripts/update_focuswave_pipeline.py; scripts/mmwave_focus_system.py"},
        {"id": "heart_rate", "status": "achieved", "claim": f"{summary['quality']['hr_n']}/{summary['complete_subjects']} 名有效被试可提取研究性心率", "evidence": "output/E_Data_FAST/final_summary.json"},
        {"id": "breath_rate", "status": "partial", "claim": f"仅 {summary['quality']['br_12_25']}/{summary['complete_subjects']} 名被试落入探索性 12–25 次/分范围", "evidence": "output/E_Data_FAST/final_summary.json"},
        {"id": "hrv", "status": "partial", "claim": f"短窗 HRV 可计算但不可靠；新增严格门控 100 窗独立验证中 RMSSD MAE={acq_validation['hrv_rmssd']['mae_ms']:.1f} ms，暂不用于正式状态判定", "evidence": "output/ACQ_reference_20260821/acq_reference_validation_summary.json"},
        {"id": "breath_method_reference", "status": "partial", "claim": f"同步呼吸带 100 个窗口比较显示，频谱呼吸率 MAE={breath_reference['summary']['spectral_mae_bpm']:.2f} 次/分，优于峰间隔法 {breath_reference['summary']['time_mae_bpm']:.2f}，但仍不足以称为高精度呼吸率", "evidence": "output/ACQ_reference_20260821/breath_method_comparison_current.json; output/ACQ_reference_20260821/breath_harmonic_correction_evaluation.json"},
        {"id": "cross_subject_attention", "status": "not_achieved", "claim": f"跨被试 AUC={lopo['focus_vs_all_nonfocus']['auc']:.3f}，尚未形成稳定专注分类器", "evidence": "output/E_Data_FAST/focus_lopo.json"},
        {"id": "personalized_attention", "status": "exploratory", "claim": "个体化时间切分结果有信号，但覆盖不足，不能作为泛化证据", "evidence": "output/E_Data_FAST/personalized_temporal_lopo.json"},
        {"id": "behavior_criterion", "status": "achieved_as_external_criterion", "claim": "SART 行为结果已按同一时间门控对齐，行为效标信号明显强于毫米波单模态", "evidence": "output/E_Data_FAST/behavior_outcome_audit.json; output/E_Data_FAST/mmwave_behavior_criterion.json"},
        {"id": "behavior_supervised_mmwave", "status": "not_achieved", "claim": f"以正确率低于 95% 为客观行为目标时，毫米波跨被试 AUC={behavior_supervised['analyses']['mmwave_only']['auc']:.3f}，尚未复现行为表现下降", "evidence": "output/E_Data_FAST/behavior_supervised_lopo.json"},
        {"id": "crossmodal_time_gate", "status": "achieved_timestamp_audit", "claim": f"{crossmodal['n_subjects']} 名被试的 RGB/NIR/毫米波时间戳均按 SART 区间审计，前后无效段已排除", "evidence": "output/E_Data_FAST/crossmodal_time_gate.json"},
        {"id": "crossmodal_features", "status": "exploratory_proxy_extracted", "claim": "已从 AVI 提取 RGB 运动/亮度与 NIR 暗核心/眼部对比度代理；尚未完成校准瞳孔直径和人脸关键点提取", "evidence": "output/E_Data_FAST/crossmodal_features_all.csv"},
        {"id": "crossmodal_exploratory_fusion", "status": "exploratory", "claim": f"已提取 {visual_fusion['n_matched_windows']} 个时间门控 RGB/NIR 代理窗口；视觉代理与毫米波融合的跨被试结果仍需按真实瞳孔/人脸关键点方法复核", "evidence": "output/E_Data_FAST/crossmodal_features_all.csv; output/E_Data_FAST/crossmodal_fusion_lopo.json"},
        {"id": "crossmodal_within_subject", "status": "exploratory", "claim": f"个体内留一验证融合 AUC={visual_within['analyses']['focus_vs_all']['mmwave_rgb_nir']['auc']:.3f}，只支持个体化研究提示", "evidence": "output/E_Data_FAST/crossmodal_within_subject_lopo.json"},
        {"id": "personalized_runtime", "status": "research_prototype", "claim": f"前半段校准后半段评分，毫米波完成 {temporal_runtime['mmwave_only']['n_scored_subjects']}/{temporal_runtime['mmwave_only']['n_subjects']} 名被试校准，融合完成 {temporal_runtime['mmwave_rgb_nir']['n_scored_subjects']}/{temporal_runtime['mmwave_rgb_nir']['n_subjects']} 名；融合后半段专注 vs 走神 AUC={temporal_runtime['mmwave_rgb_nir']['evaluations']['focus_vs_mind_wandering']['auc']:.3f}，质量不足时输出不可判定", "evidence": "output/E_Data_FAST/personalized_temporal_runtime.json; scripts/personalized_temporal_runtime.py"},
        {"id": "expanded_vital_features", "status": "exploratory", "claim": f"加入窗口呼吸率和 HR 信号质量特征后，专注 vs 走神跨被试 AUC={augmented['analyses']['focus_vs_mw']['expanded']['auc']:.3f}；视觉代理加入后反而下降，故暂不作为默认输入", "evidence": "output/E_Data_FAST/augmented_vitals_lopo.json"},
        {"id": "expanded_personalized_runtime", "status": "research_prototype", "claim": f"增强生理特征个体化后半段融合评分覆盖 {expanded_runtime['mmwave_rgb_nir']['n_scored_subjects']}/{expanded_runtime['mmwave_rgb_nir']['n_subjects']} 名被试，专注 vs 走神后半段 AUC={expanded_runtime['mmwave_rgb_nir']['evaluations']['focus_vs_mind_wandering']['auc']:.3f}，仍需独立队列验证", "evidence": "output/E_Data_FAST/personalized_temporal_runtime_expanded.json"},
        {"id": "behavior_assisted_runtime", "status": "research_prototype", "claim": f"行为辅助模式使用探针前 60 秒 SART 指标，增强毫米波+RGB/NIR+行为后半段专注 vs 走神 AUC={behavior_runtime['mmwave_rgb_nir_behavior']['evaluations']['focus_vs_mind_wandering']['auc']:.3f}，被试 bootstrap 95% CI=[{behavior_runtime['mmwave_rgb_nir_behavior']['evaluations']['focus_vs_mind_wandering']['subject_bootstrap']['auc_2.5_50_97.5'][0]:.3f},{behavior_runtime['mmwave_rgb_nir_behavior']['evaluations']['focus_vs_mind_wandering']['subject_bootstrap']['auc_2.5_50_97.5'][2]:.3f}]；不代表纯毫米波性能", "evidence": "output/E_Data_FAST/personalized_temporal_runtime_behavior.json; output/E_Data_FAST/behavior_probe_windows.csv"},
        {"id": "exported_personalized_runtime", "status": "research_prototype", "claim": f"已导出 {exported_runtime['n_models']} 个被试校准模型并完成独立后半段评分审计，{exported_runtime['independent_test_audit']['n_test_windows']} 个质量通过窗口的专注 vs 走神 AUC={exported_runtime['independent_test_audit']['focus_vs_mind_wandering_auc']:.3f}；仍不代表跨被试泛化或部署性能", "evidence": "output/E_Data_FAST/personalized_scores_validated_behavior.json; scripts/score_personalized_models.py"},
        {"id": "exported_nonbehavior_runtime", "status": "research_prototype", "claim": f"不输入行为特征时，毫米波个体化独立后半段 AUC={mmwave_exported['independent_test_audit']['focus_vs_mind_wandering_auc']:.3f}，毫米波+RGB/NIR AUC={mmwave_visual_exported['independent_test_audit']['focus_vs_mind_wandering_auc']:.3f}；两者均仍需更大独立队列验证", "evidence": "output/E_Data_FAST/personalized_scores_mmwave.json; output/E_Data_FAST/personalized_scores_mmwave_rgb_nir.json"},
        {"id": "target_100", "status": "not_achieved", "claim": f"有效被试 {target['processed_subjects']}/100；严格前后段标签配额达标 {target['subjects_ready_for_personalized_validation']} 人", "evidence": "output/E_Data_FAST/target_100_audit.json"},
        {"id": "external_physiology", "status": "achieved_as_independent_audit", "claim": f"外部数据完成 {ext['n_sessions']} 个会话、{ext['n_participants']} 名参与者审计，不含专注标签", "evidence": "output/External_AgeBalanced/summary.json"},
        {"id": "acq_reference_validation", "status": "achieved_as_independent_audit", "claim": f"BIOPAC ECG/RSP 与毫米波严格按行为时间戳完成 {acq_validation['paired_windows']} 个窗口、{acq_validation['subjects_with_sart_reference_windows']} 名被试验证；HR 课程估计 MAE={acq_validation['heart_rate_course']['mae_bpm']:.2f} bpm，呼吸频谱 MAE={acq_validation['respiration_spectral']['mae_bpm']:.2f} 次/分", "evidence": "output/ACQ_reference_20260821/ACQ_reference_validation_20260822.md; output/ACQ_reference_20260821/acq_reference_validation_scatter.png"},
        {"id": "acq_signal_quality", "status": "achieved_as_quality_proxy_audit", "claim": f"严格参照队列心动硬门控可用比例中位数={signal_quality['median_summary']['heart_signal_usable_ratio_pct']['median']:.1f}%，高/中质量点比例={signal_quality['median_summary']['heart_usable_quality_pct']['median']:.1f}%；该结果是算法质量代理，不是标定 dB SNR", "evidence": "output/ACQ_reference_20260821/ACQ_signal_quality_audit_20260822.md; output/ACQ_reference_20260821/acq_signal_quality_audit.json"},
        {"id": "release_consistency", "status": "achieved", "claim": f"发布一致性检查状态为 {release['status']}", "evidence": "output/E_Data_FAST/release_verification.json"},
        {"id": "source_coverage", "status": "achieved_inventory", "claim": f"已建立 {len(source_evidence['sources'])} 个用户指定来源的覆盖索引，并明确主行为队列、正式实验层、ECG/RSP 参照层、程序包、零散数据、文献和申请书的证据边界", "evidence": "output/E_Data_FAST/source_evidence_audit.json; scripts/audit_source_evidence.py"},
    ]
    if enhanced_visual is not None:
        requirements.append({"id": "enhanced_visual_audit", "status": "exploratory_not_default", "claim": f"加入人脸框和 NIR 瞳孔几何代理后，专注 vs 走神跨被试 AUC={enhanced_visual['analyses']['focus_vs_mw']['enhanced_visual']['auc']:.3f}，未改善现有视觉代理，故不纳入默认输入", "evidence": "output/E_Data_FAST/crossmodal_features_enhanced_all.csv; output/E_Data_FAST/augmented_vitals_enhanced_visual_lopo.json"})
    result = {"overall_status": "research_prototype_ready_final_validation_pending", "requirements": requirements, "interpretation": "The system is implemented for research use, but the scientific claim of a generalizable mmWave attention classifier remains unverified.", "next_gate": "Collect a homogeneous 100-subject cohort with repeated focus and mind-wandering probes in both calibration and test halves, plus a larger synchronized ECG/RSP subset."}
    path = OUT / "project_completion_audit.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
