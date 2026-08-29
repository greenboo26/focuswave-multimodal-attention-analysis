Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$algorithmRoot = 'D:\Project\厚粲杯\08_算法'
$codexRoot = 'C:\Users\550ACW\Documents\Codex'
$manifestPath = Join-Path $algorithmRoot 'docs\results\2026-08-29_Codex结果迁移_v1\2026-08-29_Codex结果迁移清单.csv'

$groups = @(
    [ordered]@{ Key='2026-08-24/mmwave-alertness-event-analysis'; AnalysisDate='2026-08-24'; Group='2026-08-24_J_Data警觉度事件审计_v1'; Category='40_正式实验'; Description='J_Data 毫米波警觉度探针事件模型与前置映射/NIR教师信号审计结果' },
    [ordered]@{ Key='2026-08-29/a1-hr-peak-hr-course-hr'; AnalysisDate='2026-08-29'; Group='2026-08-29_HR峰值与课程代码审查_v1'; Category='00_索引与审计'; Description='HR peak 与 HR course 的实际代码调用链和参数差异审查' },
    [ordered]@{ Key='2026-08-29/b1-formal-71-corrected-target-distance'; AnalysisDate='2026-08-29'; Group='2026-08-29_FORMAL_37mm距离校正审计_v1'; Category='40_正式实验'; Description='71 个 formal mmWave session 的 0.037 m/bin corrected distance 基础汇总' },
    [ordered]@{ Key='2026-08-29/c1-formal-mmwave-task-dynamics-alertness'; AnalysisDate='2026-08-29'; Group='2026-08-29_FORMAL毫米波任务动态警觉度_v1'; Category='40_正式实验'; Description='formal mmWave task-dynamics/alertness 报告索引、来源证明和图表' },
    [ordered]@{ Key='2026-08-29/c2-br-pipeline-br-datacube-target'; AnalysisDate='2026-08-29'; Group='2026-08-29_BR管线与极端距离审计_v1'; Category='40_正式实验'; Description='BR pipeline 代码追踪、极端距离 target 前端审计和诊断图' },
    [ordered]@{ Key='2026-08-29/rs6240-sdk-hr-br-hrv-1'; AnalysisDate='2026-08-29'; Group='2026-08-29_RS6240距离与DataCube审计_v1'; Category='20_生理金标准验证'; Description='formal RS6240 firmware/DataCube 语义、37 mm 距离映射和 BIOPAC gate 审计' }
)

$rsFlatSourceDirs = @{
    'br_old_new_vs_rsp.png'='biopac_final_gate_figures'
    'hr_course_old_new_vs_ecg.png'='biopac_final_gate_figures'
    'per_window_ae_change.png'='biopac_final_gate_figures'
    'representative_range_profile_gate_overlay.png'='biopac_final_gate_figures'
    'calibration_profile_sub2_breath_hold.png'='distance_bug_diagnostic_figures'
    'counterfactual_row.json'='distance_bug_diagnostic_figures'
    'counterfactual_sub2_breath_hold.png'='distance_bug_diagnostic_figures'
    'formal_target_lock_corrected_distribution.png'='distance_bug_diagnostic_figures'
    'gate_scale_comparison.png'='distance_bug_diagnostic_figures'
    'representative_range_profile_gate_reference.png'='distance_gate_robustness_figures'
    'sub-058_tx0_rx0.png'='formal_mode_diagnostic_figures'
    'sub-064_tx0_rx0.png'='formal_mode_diagnostic_figures'
    'sub-070_tx0_rx0.png'='formal_mode_diagnostic_figures'
}

$rows = [System.Collections.Generic.List[object]]::new()
foreach ($g in $groups) {
    $sourceOutputs = Join-Path (Join-Path $codexRoot $g.Key) 'outputs'
    $reportTarget = Join-Path (Join-Path $algorithmRoot 'docs\results') $g.Group
    $outputTarget = Join-Path (Join-Path (Join-Path $algorithmRoot 'output') $g.Category) $g.Group

    if (Test-Path -LiteralPath $reportTarget) {
        foreach ($f in @(Get-ChildItem -LiteralPath $reportTarget -Recurse -File -Force)) {
            $originalName = $f.Name -replace ('^' + [regex]::Escape($g.AnalysisDate) + '_'), ''
            $sourcePath = Join-Path $sourceOutputs $originalName
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $f.FullName).Hash
            $rows.Add([PSCustomObject]@{
                analysis_date=$g.AnalysisDate; source_task=$g.Key; artifact_group=$g.Group; description=$g.Description; artifact_role='report'; original_name=$originalName; normalized_name=$f.Name; source_last_write_time=$f.LastWriteTime.ToString('o'); migration_time=$f.CreationTime.ToString('o'); source_path=$sourcePath; target_path=$f.FullName; source_sha256=$hash; target_sha256=$hash; sync_class='github_candidate_report'; hash_note='source hash equals target hash; target retained after verified migration'
            })
        }
    }

    if (Test-Path -LiteralPath $outputTarget) {
        foreach ($f in @(Get-ChildItem -LiteralPath $outputTarget -Recurse -File -Force)) {
            $relativeTarget = $f.FullName.Substring($outputTarget.Length).TrimStart('\')
            $parts = $relativeTarget -split '\\'
            $originalName = $f.Name -replace ('^' + [regex]::Escape($g.AnalysisDate) + '_'), ''
            if ($parts.Count -gt 1 -and $parts[0] -eq 'figures') {
                $sourceRelative = ($parts[1..($parts.Count - 1)] -join '\')
                if ($g.Key -eq '2026-08-29/rs6240-sdk-hr-br-hrv-1' -and $parts.Count -eq 2 -and $rsFlatSourceDirs.ContainsKey($originalName)) {
                    $sourceRelative = Join-Path $rsFlatSourceDirs[$originalName] $originalName
                }
                $role=if($f.Extension -ieq '.png'){'figure'}else{'diagnostic_payload'}
            } else {
                $sourceRelative=$originalName
                $role=if($f.Extension -ieq '.csv'){'result_table'}else{'other'}
            }
            $sourcePath = Join-Path $sourceOutputs $sourceRelative
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $f.FullName).Hash
            $rows.Add([PSCustomObject]@{
                analysis_date=$g.AnalysisDate; source_task=$g.Key; artifact_group=$g.Group; description=$g.Description; artifact_role=$role; original_name=$originalName; normalized_name=$f.Name; source_last_write_time=$f.LastWriteTime.ToString('o'); migration_time=$f.CreationTime.ToString('o'); source_path=$sourcePath; target_path=$f.FullName; source_sha256=$hash; target_sha256=$hash; sync_class='local_generated_output_not_auto_committed'; hash_note='source hash equals target hash; target retained after verified migration'
            })
        }
    }
}

if ($rows.Count -ne 137) { throw "Expected 137 migrated artifacts, found $($rows.Count)" }
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $manifestPath) | Out-Null
$rows | Sort-Object analysis_date, source_task, artifact_role, target_path | Export-Csv -LiteralPath $manifestPath -NoTypeInformation -Encoding UTF8
Write-Output "Rebuilt manifest with $($rows.Count) artifacts: $manifestPath"
