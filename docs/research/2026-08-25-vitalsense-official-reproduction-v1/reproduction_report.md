# C1B official VitalSense reproduction v1

Status: `OFFICIAL_REPRO_COMPLETE`

## Execution

The official repository was run at commit `d9f71f96800da7ed2192ff1dc0cba0f0ef5b6de6` using MATLAB R2024b Update 1 and Signal Processing Toolbox R2024b. The official sample `C_chest_normal_withECG.mat` completed through HRestim, the official pulse-template/RWAMF route and MATLAB `findpeaks`. The sample produced HR values of 89.70 bpm by FFT, 90.00 bpm by peak count and 92.6576 bpm by inter-beat intervals.

The VS_DATASET adapter then completed all 48 sessions (VS01–VS24 × Resting/Apnea). It supplied `VitalSig`, `Radar.fs` and `Radar.t_frame` at the input boundary only; the official cardiac stages and parameters were not changed. Official beat times are in `official_beats/`, session summaries in `official_session_results.csv`, and the MATLAB console in `official_batch_matlab_console.log`.

## Evaluation

Official beat times were passed to the existing C1b ECG evaluator using the same `ecg_lead2`, 500-Hz ECG axis, one-to-one matching and ±50/75/100/150-ms tolerances. The primary result is ±75 ms. The existing fixed C1b delay was retained. The separately permitted official delay diagnostic was not estimable because VS01 Resting had no official beat matches at the primary tolerance; it is not treated as a 0-ms calibration result.

Three methods were compared: `project_bandpass_peak`, `python_vitalsense_amf`, and `official_matlab_vitalsense_rw_amf`. At ±75 ms, mean overall recall was approximately .178, .134 and .156, respectively; mean HR absolute error was approximately 0.62, 0.54 and 0.60 bpm. Official MATLAB was not clearly superior in beat recall or HR error. At ±150 ms, official mean recall rose to approximately .31, but remained too low for a claim of validated beat/IBI/HRV recovery.

## Interpretation

The result is closest to CASE B, with a secondary timing-sensitivity observation: the official route can estimate average HR reasonably while strict beat-level coverage remains low, and wider timing tolerance increases recall but does not make it adequate. This is not CASE A. It is also not sufficient to attribute the problem solely to a constant timing delay, because the official VS01 calibration delay was not estimable and ±150-ms recall remained limited.

RMSSD and SDNN are retained in the evaluator output for diagnostic comparison only. This run does not support the claim that Radar IBI or HRV has been validated.

Detailed local outputs are in `D:\Project\厚粲杯\11_数据\derived\vitalsense_official_reproduction_v1\`, including `official_session_results.csv`, `official_beat_metrics_primary.csv`, `official_beat_metrics_long.csv`, `three_method_comparison.csv`, `official_evaluation_run_manifest.json`, `official_batch_matlab_console.log`, `official_sample_matlab_console.log`, and fixed VS02/VS12/VS24 Resting/Apnea overlays.
