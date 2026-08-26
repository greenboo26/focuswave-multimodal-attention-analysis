# RS6240 formal firmware and multichannel evidence

> `HISTORICAL_TECHNICAL_REFERENCE / NOT_CURRENT_HRV_DEVELOPMENT_PLAN`

This document is a curated successor to PR #1 (`docs/rs6240-firmware-multichannel-plan-20250825@53c5814e518ebb43a6288860591f3f44feb17abd`). It preserves hardware and firmware provenance only. It does not reopen beat-to-beat HRV development, authorize a new fusion analysis, or convert candidate physiology into a formal result.

## Frozen evidence

- Device: POSSUMIC RS6240 / MRS6240-P2512, 2T4R AiP.
- Formal firmware image: `mrs6240_p2512.img`, 233,280 bytes, SHA-256 `7a8ca41d0b2438384c8a02c5abba95b265cd8984ed911414157b74f80c1fd5c8`, build `Jul 24 2026 21:33:39`.
- High-confidence acquisition parameters: 57 GHz start frequency, 256 range FFT, approximately 37 mm range resolution, approximately 4.05 GHz sweep bandwidth, 32 Doppler FFT, 250 mm/s velocity resolution, 10 ms nominal frame period, 100 Hz nominal slow-time rate, 2T4R.
- Data domain: `ReportDataCube1D`, 8-channel complex range-domain data, conceptually `frame x range_bin x virtual_channel`; this is not raw fast-time ADC and must not be range-FFT'd again as raw ADC.
- SDK `MMW_ANT_GEOMETRY_A43` virtual-channel order is documented as `0..7 = tx0_rx0..tx0_rx3, tx1_rx0..tx1_rx3`; vertical installation subsets are azimuth `{0,1,4,5}` and elevation `{3,2,1}`.

## Unresolved technical boundaries

The formal 1D output path has not been proven to apply antenna gain/phase calibration. The firmware string `MIMO Calib Load` is not sufficient evidence. TDM Tx order, Tx interval, the meaning of `interval_us=57`, NVM coefficient provenance, and board calibration continuity remain unresolved.

The existing mmWave implementation is therefore described as multi-channel candidate search / best-channel selection, not validated 8-channel fusion or MIMO beamforming. Any future fusion must be a separately frozen ablation and must be evaluated against ECG beat-to-beat evidence. Respiratory harmonics can produce coherent but incorrect cardiac candidates.

## Source and preservation

Source PR head: `53c5814e518ebb43a6288860591f3f44feb17abd`. The original branch is retained by `archive/20260826/retired/docs-rs6240-firmware-multichannel-plan-20250825` and is not merged. This curated reference is the only current repository successor required for the technical facts above.
