param(
    [string]$CodexRoot = 'C:\Users\550ACW\Documents\Codex',
    [string]$AlgorithmRoot = 'D:\Project\厚粲杯\08_算法',
    [string]$ManifestPath = 'D:\Project\厚粲杯\08_算法\docs\results\2026-08-29_Codex结果迁移_v1\2026-08-29_Codex结果迁移清单.csv'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$migrationTime = Get-Date

$groups = @(
    [ordered]@{
        Key = '2026-08-24/mmwave-alertness-event-analysis'
        AnalysisDate = '2026-08-24'
        Group = '2026-08-24_J_Data警觉度事件审计_v1'
        OutputCategory = '40_正式实验'
        Description = 'J_Data 毫米波警觉度探针事件模型与前置映射/NIR教师信号审计结果'
    },
    [ordered]@{
        Key = '2026-08-29/a1-hr-peak-hr-course-hr'
        AnalysisDate = '2026-08-29'
        Group = '2026-08-29_HR峰值与课程代码审查_v1'
        OutputCategory = '00_索引与审计'
        Description = 'HR peak 与 HR course 的实际代码调用链和参数差异审查'
    },
    [ordered]@{
        Key = '2026-08-29/b1-formal-71-corrected-target-distance'
        AnalysisDate = '2026-08-29'
        Group = '2026-08-29_FORMAL_37mm距离校正审计_v1'
        OutputCategory = '40_正式实验'
        Description = '71 个 formal mmWave session 的 0.037 m/bin corrected distance 基础汇总'
    },
    [ordered]@{
        Key = '2026-08-29/c1-formal-mmwave-task-dynamics-alertness'
        AnalysisDate = '2026-08-29'
        Group = '2026-08-29_FORMAL毫米波任务动态警觉度_v1'
        OutputCategory = '40_正式实验'
        Description = 'formal mmWave task-dynamics/alertness 报告索引、来源证明和图表'
    },
    [ordered]@{
        Key = '2026-08-29/c2-br-pipeline-br-datacube-target'
        AnalysisDate = '2026-08-29'
        Group = '2026-08-29_BR管线与极端距离审计_v1'
        OutputCategory = '40_正式实验'
        Description = 'BR pipeline 代码追踪、极端距离 target 前端审计和诊断图'
    },
    [ordered]@{
        Key = '2026-08-29/rs6240-sdk-hr-br-hrv-1'
        AnalysisDate = '2026-08-29'
        Group = '2026-08-29_RS6240距离与DataCube审计_v1'
        OutputCategory = '20_生理金标准验证'
        Description = 'formal RS6240 firmware/DataCube 语义、37 mm 距离映射和 BIOPAC gate 审计'
    }
)

$manifestDir = Split-Path -Parent $ManifestPath
New-Item -ItemType Directory -Force -Path $manifestDir | Out-Null

$rows = [System.Collections.Generic.List[object]]::new()

foreach ($g in $groups) {
    $sourceOutputs = Join-Path (Join-Path $CodexRoot $g.Key) 'outputs'
    if (-not (Test-Path -LiteralPath $sourceOutputs -PathType Container)) {
        throw "Missing source output directory: $sourceOutputs"
    }

    $reportTarget = Join-Path (Join-Path $AlgorithmRoot 'docs\results') $g.Group
    $outputTarget = Join-Path (Join-Path (Join-Path $AlgorithmRoot 'output') $g.OutputCategory) $g.Group

    $sourceFiles = @(Get-ChildItem -LiteralPath $sourceOutputs -Recurse -File -Force)
    foreach ($sourceFile in $sourceFiles) {
        $relative = $sourceFile.FullName.Substring($sourceOutputs.Length).TrimStart('\')
        $relativeParts = $relative -split '\\'
        $isReport = $sourceFile.Extension -ieq '.md'
        $role = if ($isReport) { 'report' } elseif ($sourceFile.Extension -ieq '.csv') { 'result_table' } elseif ($sourceFile.Extension -ieq '.png') { 'figure' } else { 'other' }

        if ($isReport) {
            $targetRoot = $reportTarget
            $targetRelativeDir = ''
        } else {
            $targetRoot = $outputTarget
            $targetRelativeDir = ''
            if ($relativeParts.Count -gt 1) {
                # Keep the original figure-group and nested counterfactual directories.
                # This prevents same-basename files from different diagnostic groups
                # (for example, two gate_scale_comparison.png files) from colliding.
                $targetRelativeDir = Join-Path 'figures' (($relativeParts[0..($relativeParts.Count - 2)]) -join '\')
            }
        }

        $normalizedName = '{0}_{1}' -f $g.AnalysisDate, $sourceFile.Name
        $targetDir = if ($targetRelativeDir) { Join-Path $targetRoot $targetRelativeDir } else { $targetRoot }
        $targetPath = Join-Path $targetDir $normalizedName

        if (Test-Path -LiteralPath $targetPath) {
            throw "Target already exists; refusing to overwrite: $targetPath"
        }

        New-Item -ItemType Directory -Force -Path $targetDir | Out-Null
        $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceFile.FullName).Hash
        Copy-Item -LiteralPath $sourceFile.FullName -Destination $targetPath
        $targetHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $targetPath).Hash
        if ($sourceHash -ne $targetHash) {
            Remove-Item -LiteralPath $targetPath -Force
            throw "Hash mismatch after copy; source retained: $($sourceFile.FullName)"
        }
        Remove-Item -LiteralPath $sourceFile.FullName -Force

        $rows.Add([PSCustomObject]@{
            analysis_date = $g.AnalysisDate
            source_task = $g.Key
            artifact_group = $g.Group
            description = $g.Description
            artifact_role = $role
            original_name = $sourceFile.Name
            normalized_name = $normalizedName
            source_last_write_time = $sourceFile.LastWriteTime.ToString('o')
            migration_time = $migrationTime.ToString('o')
            source_path = $sourceFile.FullName
            target_path = $targetPath
            source_sha256 = $sourceHash
            target_sha256 = $targetHash
            sync_class = if ($isReport) { 'github_candidate_report' } else { 'local_generated_output_not_auto_committed' }
        })
    }
}

$rows | Export-Csv -LiteralPath $ManifestPath -NoTypeInformation -Encoding UTF8
Write-Output "Migrated $($rows.Count) files. Manifest: $ManifestPath"
