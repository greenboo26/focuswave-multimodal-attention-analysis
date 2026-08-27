import numpy as np

from pipelines.mmwave.ecg_reference_v1 import detect_ecg_reference_v1, window_hr_from_reference


def synthetic_ecg(fs=250.0, duration_s=60.0, bpm=72.0, polarity=1.0):
    time = np.arange(0.0, duration_s, 1.0 / fs)
    frequency_hz = bpm / 60.0
    signal = polarity * (
        np.sin(2 * np.pi * frequency_hz * time)
        + 0.15 * np.sin(4 * np.pi * frequency_hz * time)
    )
    return time, signal


def test_ecg_reference_detects_positive_peaks_and_window_hr():
    time, signal = synthetic_ecg()
    reference = detect_ecg_reference_v1(time, signal)
    window = window_hr_from_reference(reference, 5.0, 35.0)
    assert reference.status == "pass"
    assert window.status == "pass"
    assert abs(window.hr_bpm - 72.0) < 1.0
    assert window.beat_count >= 10


def test_ecg_reference_selects_negative_polarity():
    time, signal = synthetic_ecg(polarity=-1.0)
    reference = detect_ecg_reference_v1(time, signal)
    assert reference.status == "pass"
    window = window_hr_from_reference(reference, 5.0, 35.0)
    assert window.status == "pass"
    assert abs(window.hr_bpm - 72.0) < 1.0


def test_ecg_reference_rejects_flatline():
    time = np.arange(0.0, 30.0, 1.0 / 250.0)
    reference = detect_ecg_reference_v1(time, np.zeros_like(time))
    assert reference.status == "fail"
    assert reference.rejection_reason == "ECG_FLATLINE"


def test_ecg_reference_rejects_nonmonotonic_timestamps():
    time, signal = synthetic_ecg()
    time[100:220] = time[99]
    reference = detect_ecg_reference_v1(time, signal)
    assert reference.status == "fail"
    assert reference.rejection_reason == "TIMESTAMP_NONMONOTONIC"
