# BR pipeline code trace

状态：PASS（代码追踪完成；只读）

日期：2026-08-29

## Scope and source state

本追踪针对当前工作树中的 FocusWave 多模态注意力分析仓库：

`D:\Project\厚粲杯\08_算法`

项目身份由 `D:\Project\厚粲杯\08_算法\AI_PROJECT.md` 解析为 `FocusWave multimodal attention analysis`；代码来源是当前工作树，不依据注释或变量名单独推断。仓库当时分支为 `codex/q1-questionnaire-criterion-validity-20260826`，工作树存在其他用户修改；本任务没有修改该仓库。以下路径均为本次读取的实际文件路径。

核心 producer 文件 SHA-256：

`D:\Project\厚粲杯\08_算法\scripts\process_vital_signs_v3_1_1.py`

`DA3E9692463508B234B744532097D0C6FF3DCA056FA5E748B6C25967E3A5C639`

## Verified execution chain

```text
DataCube NPZ parts
  -> collect_npz_parts -> _load_chunk -> stack tx* as complex64 [frame, bin, channel]
  -> accumulate_range_profile (mean |IQ|^2 over selected frames)
  -> distance gate 0.30–1.50 m, bin_spacing=0.08 m, bias=0
  -> select_separate_channels_bins
       -> per-channel candidate bins
       -> BR bin = max(br_snr * phase_stability)
       -> BR channel/bin = max per-channel BR score
  -> extract_displacement_separate
       -> unwrap phase at BR channel/bin
       -> displacement = 5.0 mm * unwrapped_phase / (4*pi)
  -> _select_breath_candidate
       -> branch A: linear detrend -> 4th-order zero-phase bandpass 0.10–0.50 Hz
       -> branch B: linear detrend -> first difference -> 5-sample moving mean
                    -> 4th-order zero-phase bandpass 0.10–0.50 Hz
       -> score both branches; retain higher-scoring branch
  -> estimate_breath_rate_consensus
       -> time-domain peak candidates + autocorrelation period hint
       -> Hann periodogram candidates in 0.10–0.50 Hz
       -> close-to-time candidate / half-harmonic rule / top spectral candidate
       -> final robust peak detection
  -> _analyze_displacement_v23
       -> BR freq_bpm = selected frequency * 60
       -> BR time_bpm = 60*FS / mean peak interval
       -> confidence = high/medium/low from |freq-time| <= 2/5 bpm
  -> save_result
       -> JSON: breath_rate{freq_bpm,time_bpm,n_peaks,confidence}
       -> NPZ: breath, breath_peaks, chest_bin, best_ch
  -> optional external RSP/reference path (separate from producer BR output)
```

## 1. Producer entry and callers

The callable producer entry is `analyze_long_record()` at lines 2960–3059 of `process_vital_signs_v3_1_1.py`. It selects `_analyze_long_record_v23` unless both `forced_heart_ch` and `forced_heart_bin` are supplied; the forced-heart branch changes HR target selection only, while its distance-gate metadata is BR-only because HR is already forced (`:2717–2782`). The BR path remains `select_separate_channels_bins()` plus `extract_displacement_separate()`.

Verified active callers in the current tree:

- `scripts\run_timeline_gated_mmwave_quality.py:70–108`: with `--run-analysis`, calls `analyze_long_record()` once for each baseline and each independently mapped task block. Without that flag it only builds the behavior/timestamp manifest and does not read NPZ data (`:112–136`). Its summary reads `result.get("breathing_rate", {})`, but the producer result key is `breath_rate`; therefore that caller's copied BR summary is empty by the current code (`run_timeline...:96` vs `process...:2483`).
- `scripts\run_e_data_batch_fast.py:39–76`: calls the same producer first on a 60-s selection range, then on the full record with `forced_heart_ch/bin`; this is a fast batch caller, and it does not pass an RSP reference.
- `scripts\run_rsp_gate.py:26–59`: calls the same producer and optionally passes `acq_path`; this activates an external RSP-derived HR harmonic gate, not a different BR estimator.
- `scripts\calibrate_vmd_segments.py:230–264`: calls the producer per timestamp-mapped calibration segment; it passes `frame_start/frame_end`, `method='vmd_heart'`, and the 0.30–1.50 m range gate.
- `scripts\validate_gold_anchor.py` does not call `analyze_long_record()`. It directly calls the lower-level range-profile, channel/bin selection, displacement extraction, and a separate `extract_hr_br()` implementation (`:123–221`).

## 2. Step-by-step trace

### A. DataCube input and array construction

Code: `scripts\process_vital_signs_v3_1_1.py:1099–1143`.

`collect_npz_parts(parts_dir, pattern)` uses `Path.glob()` and sorted order. It first matches the caller's `*_datacube_part*.npz`; if the original `sub-SXQ` spelling has no match it retries lowercase `sub-sxq`. If the pattern contains `_part*.npz`, it also prepends a matching unsuffixed `*_datacube.npz` file when present (`:1131–1143`).

`_load_chunk()` opens each NPZ read-only, sorts keys starting with `tx`, stacks them on the last axis, and converts to `complex64` (`:1103–1108`). The producer therefore consumes an already range-domain DataCube-shaped array; this code does not perform a new range FFT. `_iter_selected_chunks()` maps global `frame_start/frame_end` to each part and yields only the selected frame slices (`:1115–1128`).

### B. Range profile and target/bin/channel choice

Code: `scripts\process_vital_signs_v3_1_1.py:1146–1233`, `:1374–1412`, and `_analyze_long_record_v23()` at `:2803–2900`.

1. `accumulate_range_profile()` computes `mean(abs(iq_fd)**2)` over frames and bins for each channel, accumulates across selected chunks, and divides by total selected frame count (`:1146–1172`). `N_CH=8`, `FS=100.0`, and `WAVELENGTH_MM=5.0` are module constants (`:15–18`).
2. `_analyze_long_record_v23()` constructs a distance mask using `bin * bin_spacing_m - range_bias_m`, with defaults `min_range_m=0.3`, `max_range_m=1.5`, `bin_spacing_m=0.08`, `range_bias_m=0.0` (`:2500–2517`, `:2813–2818`, `:2835–2840`). The gate is applied to both BR and HR in this normal branch (`:2873–2881`). The forced-heart runner used by the fast batch applies the same mask to BR selection but records `gate_applies_to="breath_only"` because HR is supplied by the caller (`:2750–2782`).
3. `select_separate_channels_bins()` evaluates every channel unless `channel_override` is passed (`:1374–1383`). For each channel, `select_bins_from_profile()` retains bins with mean power at least 1% of that channel's maximum; it first requires `0.1 < var(unwrapped phase) < 50`, then falls back without that phase-variance requirement if no candidate survives (`:1203–1228`).
4. For each retained bin, the code linearly detrends unwrapped phase, computes raw `abs(rfft(phi_detrended))**2`, defines noise as mean power from 2.5–5.0 Hz, then computes `hr_snr` in 0.8–2.0 Hz and `br_snr` in 0.1–0.5 Hz. BR score is `br_snr * phase_stability`; phase stability is derived from detrended phase roughness and 95th-percentile jump ratio (`:1209–1222`, `:1175–1191`).
5. Within each channel, BR and HR bins are selected independently; across channels, the BR channel/bin is the summary with maximum `best_br_score`, and the HR channel/bin is the summary with maximum `best_hr_selection_score` (`:1386–1410`). Thus BR and HR do not have to share a channel or bin. The result explicitly stores `channels.breath`, `channels.heart`, `bins.breath`, and `bins.heart` (`:2867–2871`).

### C. BR signal extraction

Code: `scripts\process_vital_signs_v3_1_1.py:1415–1439`, called at `:2864–2865`.

`extract_displacement_separate()` reads the selected frame range again. For BR it takes `angle(iq_fd[:, br_bin, br_ch])`, concatenates chunks, unwraps once over the concatenated sequence, and converts phase to displacement using `5.0/(4*pi)` mm (`:1424–1439`). The BR signal input to preprocessing is therefore one continuous selected-segment displacement vector at the chosen BR channel/bin.

### D. BR preprocessing

Code: `scripts\process_vital_signs_v3_1_1.py:273–275`, `:577–595`, `:642–679`.

`_select_breath_candidate()` creates two actual BR preprocessing candidates:

- `baseline_bandpass`: linear detrend (`signal.detrend(..., type='linear')`) followed by a 4th-order Butterworth SOS bandpass and zero-phase `sosfiltfilt`, 0.10–0.50 Hz (`:643–655`, `_sos_bandpass` at `:273–275`).
- `matlab_style_preprocess`: the same linear detrend, first difference with prepended first sample, 5-sample moving mean, then the same 4th-order zero-phase 0.10–0.50 Hz bandpass (`:591–595`, `:656–664`).

The higher `selection_score` is retained; no parameter search or runtime tuning occurs in this function (`:667–679`).

### E. BR candidate generation and selection

Code: `scripts\process_vital_signs_v3_1_1.py:397–525`, `:528–574`.

`estimate_breath_rate_consensus()` runs both domains on the selected preprocessed BR vector:

- Time domain: Savitzky–Golay smoothing with a 0.35-s window at `FS=100` (rounded to odd sample count), then autocorrelation over 6–30 bpm periods; candidate peaks use `find_peaks()` with a minimum distance of at least `60/30 s`, increased to `0.7 * reference_period` when an autocorrelation or hint period exists (`:416–447`).
- Spectral domain: `signal.periodogram(..., fs=100, window='hann')`, restricted to 0.10–0.50 Hz; spectral local peaks use `find_peaks()` with distance `len(p_band)//25`, falling back to the maximum band bin when no local peak exists (`:515–525`).
- Consensus: spectral candidates are sorted by power. If a time-domain rate exists, the strongest candidate within 0.08 Hz is selected. Otherwise, when the top frequency is at least 0.22 Hz, a half-frequency bin is accepted if it is within 0.04 Hz and has at least 35% of top power; otherwise the top spectral candidate is used (`:538–566`).
- Final peaks: `detect_peaks_breath_robust()` is run again with the selected frequency as a hint. It scores six prominence factors `[0.40, 0.32, 0.26, 0.20, 0.14, 0.10]`, checks intervals against 6–30 bpm, and repairs a gap between `1.7` and `3.0` reference periods by searching ±0.35 s (`:452–512`).

The branch score is computed by `_score_breath_candidate()` from spectral `top_power/median_power` (`snr_like`), time/frequency mismatch, roughness, and a peak-count bonus; fewer than two peaks incurs a −12 score penalty (`:598–639`). This is branch selection, not an external physiological quality validation.

### F. BR output

Code: `scripts\process_vital_signs_v3_1_1.py:2379–2497` and `:1442–1480`.

`_analyze_displacement_v23()` uses the retained BR vector and candidate frequency/peaks. It writes:

- `breath_rate.freq_bpm = br_freq * 60`;
- `breath_rate.time_bpm = 60 * FS / mean(diff(breath_peaks))` when at least two peaks exist;
- `breath_rate.n_peaks`;
- `breath_rate.confidence = high` if the absolute time/frequency gap is ≤2 bpm, `medium` if ≤5 bpm, otherwise `low` (`:2444–2449`, result schema at `:2483–2488`).

The JSON output is `<session>_mmwave_vital_signs.json` and the NPZ output is `<session>_mmwave_vital_signs.npz` (`:1447–1459`). The NPZ stores `breath`, `breath_peaks`, `chest_bin`, and `best_ch`; it does not store the BR channel as a dedicated field (`:1451–1462`). The JSON stores the selected BR channel/bin separately in `channels`/`bins` (`:2867–2871`).

BR is computed once over the full `frame_start:frame_end` segment. There is no BR sliding-window length, BR step, or BR time-course output in this producer. The `40 s / 20 s` window/step in `separate_vmd_heart_windowed()` belongs to the HR VMD path (`:1296–1371`), not to BR estimation.

### G. QC and quality gate

There are three distinct code-level QC layers; they must not be conflated:

1. **BR internal consistency label:** `_analyze_displacement_v23()` only compares full-segment `freq_bpm` and `time_bpm` and emits `high/medium/low` confidence at ≤2/≤5 bpm (`:2444–2449`). It does not reject or null BR when confidence is low.
2. **Producer hard gate:** `estimate_hr_time_course()` and `_analyze_displacement_v23()` implement a heart-signal 10-s hard gate (`window_s=10`, `min_std_mm=0.0005`, candidate minimum usable ratio 0.50) and can null HR (`:907–918`, `:1033–1062`, `:2416–2422`). This is an HR signal gate, not a BR gate; no analogous BR amplitude hard gate is called before writing `breath_rate`.
3. **External segment signal-existence scanner:** `scripts\scan_timeline_gated_quality.py:31–85` independently selects an HR bin, applies linear detrend plus HR bandpass 0.8–2.0 Hz, computes per-part standard deviations, and labels pass/partial/fail using 0.80/0.50 usable ratios against 0.0005 mm (`:57–83`). It does not calculate or gate BR.

The older whole-record `_scan_quality.py:37–104` follows the same HR-only 10-s signal-existence logic. It reports BR constants imported from the producer but does not use them in its scan body (`:29–32`, `:59–85`).

### H. RSP reference and comparison alignment

#### H1. External RSP prior path into the producer

Code: `scripts\run_rsp_gate.py:26–59`; producer path `scripts\process_vital_signs_v3_1_1.py:2903–2997`.

`run_rsp_gate.py` finds the first `*.acq` under the configured calibration subject directory, passes its path as `acq_path`, and calls `analyze_long_record()` without `frame_start/frame_end` (`:34–50`). In `analyze_long_record()`, `acq_path` is converted to one scalar `ext_br_bpm` by `estimate_respiration_bpm_from_acq()` (`:2988–2997`). The function finds the first channel whose name contains `RSP`, reads the entire channel, and first tries `gold_standard_qa.rsp_qa(rsp, sr, 0, len(rsp))`; it falls back to whole-record median peak intervals after 0.10–0.70 Hz filtering (`:2919–2957`). No time-varying RSP signal or per-window RSP-to-mmWave alignment is passed into the BR estimator.

That scalar is consumed by `respiration_harmonic_reject()` only in the HR candidate path (`:1886–1907`): it tests HR candidates against 2×/3× `ext_br_bpm` with a ±5 bpm tolerance and may prefer the time-domain HR candidate or next spectral peak. It does not change the BR candidate selected by `_select_breath_candidate()`.

#### H2. Segment-level ECG/RSP comparison path

Code: `scripts\validate_gold_anchor.py:43–153`, `:254–347`; reference cleaner `scripts\gold_standard_qa.py:134–183`.

`validate_gold_anchor.py` reads `events.csv` segment start/end Unix milliseconds, reads the third column of the mmWave timestamp CSV as Unix milliseconds, and maps each segment to mmWave frames with `np.searchsorted()` (`:54–72`, `:274–285`). For the RSP side, `load_align()` reads ECG/RSP channels from `.acq`, reconstructs marker bit values from `STP Input` channels, matches the longest common marker suffix against behavior markers, and fits `unix_ms = offset + k * acq_sample_index` (`:65–105`). `rsp_br_segment()` converts the same Unix segment endpoints back to ACQ sample indices and calls `gold_standard_qa.rsp_qa()` (`:116–121`).

The mmWave BR comparison in this script is separate code: `load_mm_segment()` selects/extracts the mmWave BR signal for the mapped frame interval, and `extract_hr_br()` applies 0.10–0.50 Hz bandpass plus `estimate_freq_periodogram()`; it returns BR as the spectral peak times 60 (`:123–153`, `:215–221`). Thus the RSP and mmWave windows share Unix-time segment boundaries, but the comparison script does not call the producer's consensus BR estimator.

`gold_standard_qa.rsp_qa()` uses the RSP segment itself, median subtraction, 4th-order zero-phase bandpass 0.10–0.70 Hz, `find_peaks(distance=0.5*sr, prominence=0.2)`, 6–42 bpm interval filtering, and median period rate (`:134–183`). It declares RSP usable at a normal-period ratio ≥0.80; this is reference-side QC.

#### H3. Probe-window comparison from stored producer NPZ

Code: `scripts\analyze_acq_reference.py:95–128`, `:172–230`; `scripts\compare_mmwave_reference.py:34–84`.

`analyze_acq_reference.py` creates reference rows from behavior probe onset times. It resolves the ACQ start from the file marker and mmWave start from `master_timeline.csv` (`mmwave_start`), with calibration/events/timestamp fallbacks (`:53–80`). It converts probe onset to ACQ-relative seconds, then computes 60-s and 30-s RSP reference metrics ending at the probe onset (`:172–230`). The RSP reference implementation here uses 0.08–0.70 Hz bandpass, peak distance 1.5 s, and valid period limits 2–10 s (`:118–128`).

`compare_mmwave_reference.py` loads the stored producer NPZ and converts `breath_peaks` to seconds using `t`. For each reference probe, it defines `tp=(onset_ms-mmwave_start_ms)/1000`, takes the default `window_s=60` interval `(tp-window_s,tp]`, and computes BR from stored breath-peak intervals constrained to 2–10 s (`:48–70`). It pairs that result with `br_rsp_bpm` or `br_rsp_bpm_30s` from the previously generated reference metrics (`:60–70`). This is the actual stored-output comparison alignment; it is not a re-run of the producer.

## 3. Requested property matrix

| Property | Actual code behavior |
|---|---|
| BR window length | Producer: entire caller-provided `frame_start:frame_end` segment; no BR sliding window. Comparison: default 60 s or explicit 30 s in `compare_mmwave_reference.py`. |
| BR frequency band | Producer BR selection/preprocessing: 0.10–0.50 Hz (6–30 bpm). RSP reference: 0.10–0.70 Hz or 0.08–0.70 Hz depending on reference script. |
| Detrend/filter | Producer BR: linear detrend; optional first difference + 5-sample moving mean; 4th-order Butterworth SOS `sosfiltfilt`, 0.10–0.50 Hz. |
| PSD/FFT/peak method | Target selection: raw `abs(rfft)^2` on detrended unwrapped phase. BR candidate: Hann periodogram + `find_peaks`, time-domain Savitzky–Golay + autocorrelation + `find_peaks`. Final BR has time and frequency values. |
| target/bin/channel selection | Mean `|IQ|^2` range profile; 0.30–1.50 m gate; per-channel bins with ≥1% max power; BR score `br_snr*phase_stability`; global max BR score across channels. |
| BR vs HR target sharing | No guarantee and normally independent. BR and HR selections are separately returned. |
| Harmonic handling | BR consensus has a top-frequency half-harmonic rule (top ≥0.22 Hz, half within 0.04 Hz, half power ≥35%). External RSP 2×/3× harmonic rejection is in HR candidate selection, not BR output. |
| Temporal tracking | No BR temporal tracking. HR has separate 40-s VMD / 20-s step and HR time-course smoothing; that is not BR tracking. |
| Quality gate | BR only gets a low/medium/high full-segment time–frequency confidence label and is not nulled. Existing hard gate is HR-only; external scanners are HR signal-existence QC. |
| RSP alignment | External-prior path uses whole ACQ RSP scalar with no temporal mapping. Comparison paths map Unix timestamps to ACQ/mmWave frames or use probe onset minus mmWave start; RSP and mmWave are then compared over the same segment/probe interval. |

## 4. Boundaries of this trace

This deliverable records code paths, call sites, parameters, outputs, and alignment mechanics only. It does not assess BR accuracy, optimize parameters, run corrected-gate comparisons, rerun formal analysis, or perform HRV analysis. No project source or raw data was modified.
