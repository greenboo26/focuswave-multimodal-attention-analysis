$ErrorActionPreference = 'Stop'

$outDir = Join-Path (Get-Location) 'docs\results\final_merge_readiness_20260829'
$files = @(
    'merge_session_availability_matrix.csv',
    'merge_probe_level_availability_matrix.csv'
)

foreach ($name in $files) {
    $path = Join-Path $outDir $name
    $rows = Import-Csv $path
    $isProbeMatrix = $rows.Count -gt 0 -and ($rows[0].PSObject.Properties.Name -contains 'probe_id')
    $newRows = foreach ($row in $rows) {
        $flagged = $row.mmwave_available -eq 'yes' -and $row.mmwave_qc_class -in @(
            'formal_qc_v1_pass_available',
            'formal_qc_v1_pass',
            'preliminary_screening_only'
        )
        $mmwaveTier = if ($flagged) { 'preliminary_screening_only' } else { 'no_preliminary_screening_flag' }
        $qcClass = if ($flagged) { 'preliminary_screening_only' } else { 'no_preliminary_screening_flag' }
        $mmwaveFeature = if ($row.usable_behavior_mmwave -in @('yes', 'preliminary_screening_only')) { 'preliminary_screening_only' } else { 'no_preliminary_screening_flag' }
        $rgbMmwaveFeature = if ($row.usable_behavior_rgb_mmwave -in @('yes', 'preliminary_screening_only')) { 'preliminary_screening_only' } else { 'no_preliminary_screening_flag' }

        $rowOut = [ordered]@{
            subject = $row.subject
            session = $row.session
            repeat_participant_id = $row.repeat_participant_id
            behavior_available = $row.behavior_available
            probe_available = $row.probe_available
            mmwave_available = $row.mmwave_available
            mmwave_qc_class = $qcClass
            mmwave_use_tier = $mmwaveTier
            rgb_available = $row.rgb_available
            rgb_qc_class = $row.rgb_qc_class
            nir_available = $row.nir_available
            nir_qc_class = $row.nir_qc_class
            usable_behavior_baseline = $row.usable_behavior_baseline
            usable_behavior_rgb = $row.usable_behavior_rgb
            usable_behavior_mmwave = $mmwaveFeature
            usable_behavior_rgb_mmwave = $rgbMmwaveFeature
            usable_full_multimodal = $row.usable_full_multimodal
            exclusion_reason = $row.exclusion_reason
        }
        if ($isProbeMatrix) {
            $rowOut.probe_id = $row.probe_id
            $ordered = [ordered]@{}
            foreach ($key in @('subject','session','repeat_participant_id','probe_id','behavior_available','probe_available','mmwave_available','mmwave_qc_class','mmwave_use_tier','rgb_available','rgb_qc_class','nir_available','nir_qc_class','usable_behavior_baseline','usable_behavior_rgb','usable_behavior_mmwave','usable_behavior_rgb_mmwave','usable_full_multimodal','exclusion_reason')) {
                $ordered[$key] = $rowOut[$key]
            }
            $rowOut = $ordered
        }
        [pscustomobject]$rowOut
    }
    $newRows | Export-Csv $path -NoTypeInformation -Encoding UTF8
}


