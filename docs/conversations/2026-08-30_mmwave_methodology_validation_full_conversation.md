# FocusWave mmWave methodology / validation conversation archive — 2026-08-30

> Archive scope: user-visible conversation content from this ChatGPT thread concerning mmWave methodology, VMD backend, DC offset/static clutter, ADC vs range-domain DataCube, preprocessing/windowing, selector/path, distance ROI/gate, HR/HRV validation, GitHub synchronization, and the T0–T7 task plan.
>
> Excluded intentionally: hidden chain-of-thought, system/developer instructions, internal tool parameters, and non-user-visible execution traces. Image-generation attempts are represented as transcript events rather than embedding binary images.
>
> Repository: `greenboo26/focuswave-multimodal-attention-analysis`
>
> Canonical companion documents created/used during this conversation:
> - `docs/canonical/MMWAVE_CANONICAL_STATE_AND_INTERFACE_V1.md`
> - `docs/canonical/MMWAVE_FRONTEND_DATA_DOMAIN_AND_VALIDATION_DECISION_2026-08-30.md`
>
> Key commits created during this conversation:
> - `7513dbe9d7c2fe0d168bb70cffd88de855965924` — `fix(mmwave): pin maintained sktime VMD backend`
> - `ed50b14fe596b2d58f3884d267b290dc4ea96366` — `docs(mmwave): correct frontend data-domain and validation roadmap`

---

## Turn 1 — User

### Selected text

#### Selection 1

> 但 requirements.txt 和 process_vital_signs_v3_1_1.py 的旧代码还没有全部改完，所以不能说代码修复已经完成。这个代码/规范不一致也被我明确写进了 canonical 文档，避免以后 AI 看到旧代码又误认为 fallback 是正式设计。

#### Selection 2

> DC offset，

#### Selection 3

> DC offset，并直接干扰生命体征相位恢复

#### Selection 4

> 335 个冻结窗口上，结果是：HR <0.30 m 选择比例确实从 36.12% 降到 24.18%。但是 HR bin 切换：50.15% → 58.41%HR channel 切换：48.32% → 55.66%BR 近端选择：7.16% → 7.46%BR channel switching 也恶化。所以结果不是“静态杂波不存在”，而是：这一版简单的 slow-time mean subtraction，没有让当前 target selector 整体变得更稳定。

#### Selection 5

> 而且我们的正式 NPZ 已经是 range-domain complex DataCube。也就是说，某些应该发生在 ADC/fast-time → Range FFT 之前的东西，例如原始 ADC Hamming window、某些硬件级 DC/IQ calibration，我们现在未必还能从现有 NPZ 重新做。

#### Selection 6

> MTI / recursive background subtraction文献有充分合理性，但 FocusWave 当前没有足够 evidence 冻结为正式新步骤I/Q DC offset calibration对 proximity stationary clutter 很有理论针对性，但当前没有正式 FocusWave A/B 证据当前 selector暂时 KEEP新 selector当前不授权重新发明目标选择后的 phase/filter继续保留现有已审计链VMD软件 backend 已确定用 sktime；VMD 本身是否作为最终 HR 必需步骤仍要服从现有科学验证

#### Selection 7

> 这个问题不能通过“哪个方法让 HR MAE 最低就选哪个”解决，否则又会过拟合外部参考。

#### Selection 8

> 所以目前正式管线不应该把 0.30–1.50 m 包装成“生理有效 gate”。如果旧代码还用它选 target，那要明确标成历史算法约束，不能把它解释成经过当前正式实验验证的距离有效区间。

#### Selection 9

> 必须先把 selector/path 固定成一样，才能研究 window length 本身。

#### Selection 10

> 现在 requirements.txt 仍然是 vmdpy>=0.2。process_vital_signs_v3_1_1.py::_load_vmd() 仍然是：sktime → except Exception → vmdpy所以正式规范与实际旧代码目前暂时存在一个已记录的 mismatch。下一次正式执行 VMD 前，这两个必须改成：requirements.txt → sktime==1.1.0以及：_load_vmd() → 只 import sktime.libs.vmdpy.VMD；检查 sktime==1.1.0；失败就明确报错；绝不换 backend并在 manifest 里写：sktime versionbackend = sktime.libs.vmdpyVMD parameterssource commit这个代码修复完成并做一次旧 vmdpy 0.2 vs sktime 1.1.0 冻结输入 parity test 后，我才会认为 VMD 依赖问题真正完全收口。

#### Selection 11

> 当前需要纠正的最后一个软件点

### User request

> 那你一起改了呀，不要增加后续工作量，说清楚是你改的就行，说已经改了，git提交的时候写清楚。
> “DC offset，”  这个是什么，为什么会干扰？
> `MTI/static clutter removal → Range FFT → spatial localization/beamforming → phase → vital signs`  翻译一下。并且和我们现在的处理步骤做对比。
> 也有论文在 Range FFT 前使用 Hamming、Blackman-Harris 等 window（窗函数）减少强目标的频谱旁瓣泄漏  ,这个也向我解释一下。
> 我们之前做了fft前的处理但是窗口切换率上升，这结果是变差了？还是意味着被试确实有往前，现在只是重新捕捉到了？为什么认为这个是恶化？为什么切换率会上升，原因知道吗？
> 我们前面对于fft和选窗之前的处理只有这一次吗？之前没有做过尝试吗？有没有结果和历史记录？
> 而且我们的正式 NPZ 已经是 **range-domain complex DataCube**。也就是说，某些应该发生在 ADC/fast-time → Range FFT 之前的东西，例如原始 ADC Hamming window、某些硬件级 DC/IQ calibration，我们现在未必还能从现有 NPZ 重新做。  你说的这个，我其实想知道，我们 参考的方法，处理的数据类型是和我们一样的吗？如果他们都是用原始ADC处理，我们是不是不应该套用这些处理方法。我其实不清楚，我们这个原始数据收起来，是什么性质，与adc的有什么不同，两者分别长什么样子，能不能给我图，并且告诉我，可以套用处理方法吗？
>
> 这个问题不能通过“哪个方法让 HR MAE 最低就选哪个”解决，否则又会过拟合外部参考。  那要靠什么判断，下一步应该尝试最可能有效的几种方法然后做对比吧？问题是要以什么指标来判断？
>
> 所以目前正式管线不应该把 0.30–1.50 m 包装成“生理有效 gate”。如果旧代码还用它选 target，那要明确标成**历史算法约束**，不能把它解释成经过当前正式实验验证的距离有效区间。  那研究一般如何确定距离门控，是否做距离门控，我觉得我们是需要的，因为我们不做锁过十几米，那里可能是另一个房间的被试，所以必须控制在近距离。不过，这个到底应该怎么定，依据什么？
>
> 必须先把 selector/path 固定成一样，才能研究 window length 本身。  所以这里是说明，我们前面对比是有问题的是吗？还有，其实这个20就不应该出现在这里对吧。
>
> 因此如果 FocusWave 以后真的做 HRV，正确逻辑应该是：
> **先证明 radar beat ≈ ECG R-peak。这要怎么做？**
>
> 当前需要纠正的最后一个软件点  这个你不能现在做吗？对于需要布置到本地的修改，你布置任务在上面，我会交给codex做。
>
> 本次对话，所有的你的解释，信息来源，决策改变，发现更正，不管是认知上的分析路径方法方向还是实际的github文件改动，你都要详细地同步到github上面的特定位置。
>
> 并且。根据我们的讨论和结论，回答完前面所有问题之后。直接纠正覆盖所有不严谨、错误的分析方向、思路、决策，并且直接分配好下一步还有到最终多模态接入前一步，毫米波要做的u送有任务

---

## Turn 2 — Assistant

> 我会把这轮当成一次**毫米波分析路线纠偏 + 代码治理收口**：先重新核验 `main`，把 VMD 依赖问题直接改掉并写清提交；再把你刚才追问的 ADC/DataCube、FFT 前处理、距离 gate、selector/window、HRV beat-level validation 全部核到公开方法和仓库历史；最后把“下一步直到多模态接入前”的任务拆成明确 GitHub 任务，不留成聊天里的口头建议。

During execution, the assistant corrected one interpretation before finalizing:

> 先回应你关于“切换率为什么能叫恶化”的质疑：**单看切换率本身，确实不能直接判定恶化。** 如果被试真实移动，正确 selector 就应该切换。前一版表述把“切换更多”过度解释成“变差”，这是需要纠正的。真正应该判断的是：切换是否对应独立的位移/姿态证据、是否保持目标轨迹物理连续、是否改善同窗 ECG/RSP 一致性、是否降低错误锁定，而不是追求“切换越少越好”。我会把这条更正同步进 canonical 记录。

A second correction was made during repository/history reconciliation:

> 我先纠正一个我上一条里说得过头的地方：**Issue #25 的 20 s vs 60 s 对比本身并不是“selector/path 不一致所以无效”。** 仓库报告明确写了：它固定了同一个 historical target、同一套 v3.1.1 bandpass/periodogram/peak/course 链，只改变 trailing window length，所以它是一个合格的**条件性诊断比较**；真正的问题是 20 s 原本就不是正式生理窗口，而且这批比较只覆盖 3 个 targeted sessions，不能据此把 60 s 直接升格成正式标准。这个更正我会一起落到 GitHub。

The assistant reported concrete GitHub changes while still working:

> 目前我已经先把两件“能直接改、不能再拖”的东西落到 `main`：`requirements.txt` 已由我本人改成 `sktime==1.1.0`，提交是 `7513dbe9...`；同时新建了一份专门的 canonical 纠偏文档，把这轮关于 **ADC/DataCube、DC offset、FFT 窗、335-window A/B 的重新解释、粗距离 ROI、20/60 s、HRV beat gate、T0–T7 任务链**全部固化，提交是 `ed50b14f...`。后面我会把对应任务直接挂回 #25/#26/#27/#29，而不是另开一堆分支或口头留待办。

### Assistant explanation and decisions

> 不会再生成图片。我现在只核对 GitHub 真实状态：`main` 最新 HEAD、VMD 代码是否真的全部改完、canonical 记录是否完整、#25/#26/#27/#29 的任务是否都已同步，然后明确告诉你“已完成 / 未完成 / 还缺什么”，不含糊。

Before that status-only follow-up, the assistant had provided the following substantive explanation.

#### 1. DC offset

DC offset was explained using a simplified selected-bin/channel complex signal:

```text
z(t) = C_static + s_vital(t) + noise(t)
```

where the desired cardiopulmonary modulation is small and `C_static = I0 + jQ0` is an approximately constant or slowly varying complex contribution. Possible physical contributors include stationary reflectors/body parts in the same finite range/angular cell, TX-RX coupling or leakage, local-oscillator/mixer leakage, circuit I/Q bias and other static clutter.

Phase extraction uses:

```text
phi(t) = arg(z(t)) = atan2(Q(t), I(t))
```

If a large static vector displaces the wanted I/Q arc/circle away from the origin, `atan2(Q,I)` no longer cleanly represents the desired micro-motion angle. This can compress or nonlinearly distort phase variation and make phase unwrapping less stable. The discussion explicitly distinguished **simple complex mean subtraction** from the broader family of DC/static-clutter calibration methods, including geometric circle fitting and dynamic center estimation.

The key correction was:

> **FocusWave 当前那一次简单 slow-time complex-mean subtraction 没有足够证据升级为正式步骤，不等于“DC offset calibration 没用”。**

#### 2. Translation of the reference processing chain

The chain:

```text
MTI/static clutter removal -> Range FFT -> spatial localization/beamforming -> phase -> vital signs
```

was translated as:

> **动目标指示（MTI）/静态杂波抑制 → 距离向 FFT（把 fast-time 拍频变成距离 bin）→ 空间定位/波束形成（利用多天线在方向上分离目标）→ 从目标复数 I/Q 提取相位/微位移 → 估计呼吸、心率、逐搏时间或 HRV。**

The assistant also corrected the implicit assumption that static-clutter removal must always occur before Range FFT: some radar implementations perform clutter suppression on the already formed radar cube.

Current audited FocusWave v3.1.1 processing was described as closer to:

```text
stored complex range-domain NPZ
-> range/channel power accumulation
-> candidate bin/channel scoring (power + HR/BR spectral evidence + phase stability)
-> target/channel selection
-> selected-bin complex phase unwrap -> displacement
-> BR detrend/diff/moving-mean/bandpass candidate logic
-> HR bandpass and, when method=vmd_heart, windowed VMD separation
-> periodogram + peak candidates
-> time/frequency/continuity fusion
-> HR/BR summaries + QC
```

The critical data-domain conclusion was that the current producer starts **after the Range-FFT boundary**.

#### 3. Hamming / Blackman-Harris before Range FFT

The assistant explained that a finite ADC record is equivalent to truncating the signal. If the beat sinusoid does not line up with FFT integer-frequency bins, energy spreads across neighboring bins, producing spectral leakage and sidelobes. For radar, sidelobes from a strong reflector can contaminate neighboring range bins and obscure weaker targets.

The operation is:

```text
RangeSpectrum[k] = FFT(ADC[n] * w[n])
```

before target-range selection.

- Hamming: lowers sidelobes relative to a rectangular window with moderate main-lobe widening.
- Blackman-Harris: stronger sidelobe suppression but a wider main lobe, so close targets can become less separable and coherent gain/amplitude changes.

The methodological conclusion was that window choice is a **resolution-versus-sidelobe trade-off**, not a universally beneficial upgrade.

The assistant also emphasized that:

> `window -> FFT` is not equivalent to taking an already FFT'd range cube and multiplying its range bins by that window.

Therefore ADC-level windowing cannot simply be retrofitted to the current NPZ unless the upstream raw/fast-time representation or acquisition-side processing can be recovered.

#### 4. Raw ADC versus FocusWave range-domain complex DataCube

Raw FMCW ADC/beat-signal data were characterized conceptually as something like:

```text
frame × chirp × RX(or virtual antenna) × fast_time_sample
```

where fast-time beat frequency mainly encodes range.

Operations possible in that domain include ADC/IF DC removal, clipping checks, I/Q calibration when applicable, fast-time Hamming/Blackman-Harris, Range FFT, FFT scaling and range calibration.

After Range FFT, a vital-sign-oriented complex range-domain representation was characterized as approximately:

```text
slow_time/frame × range_bin × channel
```

Each range bin retains a complex `I + jQ` value whose phase changes over slow time with sub-wavelength body motion.

The current producer was audited as operating on the latter domain, and the canonical status was set to:

```text
CURRENT_ARCHIVED_PRODUCER_INPUT_DOMAIN = RANGE_DOMAIN_COMPLEX
```

while deliberately keeping the upstream availability question open:

```text
ORIGINAL_PRE_RANGEFFT_DATA_AVAILABILITY = TO_VERIFY
```

The assistant explicitly avoided claiming that raw ADC never existed; instead, T1 was assigned to recover whether raw ADC/fast-time data were ever retained, what Range-FFT window/scaling/DC calibration happened upstream, and whether antenna/channel geometry and phase calibration are available.

#### 5. Reinterpretation of the 335-window mean-subtraction A/B

Frozen A/B:

- A: current range-domain mean-power profile and current v3.1.1 selector.
- B: slow-time complex mean subtraction on the already range-domain cube, followed by the same selector/path logic.

Observed values discussed:

- candidate availability: 335/335 in both.
- HR selected below 0.30 m: 36.1194% -> 24.1791%.
- HR bin switch: 50.1529% -> 58.4098%.
- HR channel switch: 48.3180% -> 55.6575%.
- BR selected below 0.30 m: 7.1642% -> 7.4627%.
- BR channel switching increased.

The earlier wording “switching increased, therefore the method got worse” was retracted. The corrected conclusion was:

```text
B materially changes target-selection behavior and reduces near-side HR selections,
but it does not establish that the extra switches are correct or incorrect.
```

Possible mechanisms recorded as hypotheses included:

1. removing a stable complex component could reduce winner/runner-up score margins so noise/multipath candidates exchange rank more often;
2. dynamic components previously hidden under a strong static component may become more prominent;
3. true participant/posture movement may become easier to follow;
4. a simple global/within-window mean could distort a nonstationary wanted I/Q trajectory or remove part of useful low-frequency content.

The A/B lacked independent per-window motion/placement truth, so the formal decision remained:

```text
DO_NOT_PROMOTE_THIS_MEAN_SUBTRACTION
```

for **insufficient validated benefit / ambiguous switching correctness**, not because low switching is intrinsically better.

#### 6. Historical preprocessing and prior attempts

The assistant found that historical mmWave work was broader than this one A/B. Repository evidence records historical exploration involving VMD, SSA/VMD, adaptive notch/harmonic handling, multi-bin/channel approaches and a historical `scripts/experiment_*.py` family including CEEMDAN, Hampel, phase-difference, CFAR, envelope and SPC-style alternatives.

However, some historical exact parameter/result tables are incomplete, so those entries were treated as provenance rather than validated reusable methods.

The 335-window slow-time complex-mean subtraction run was characterized as the strongest same-denominator controlled pre-selector front-end A/B currently in the evidence chain. No canonical evidence had yet established a controlled raw-ADC pre-Range-FFT Hamming/Blackman-Harris A/B.

T1 was therefore assigned to build a provenance matrix:

```text
method | required data domain | available? | exact prior script/commit |
parameters/results | reusable? | unresolved gap
```

#### 7. How to compare preprocessing / selector methods without overfitting ECG MAE

The assistant clarified that ECG/RSP reference remains essential for final physiological validation, but should not be repeatedly used to tune every front-end parameter on the same subjects.

A three-stage hierarchy was frozen:

**Stage A — physics/data-domain gate**

A candidate is considered only if its required input domain exists, it targets a documented failure mechanism, and core parameters come from hardware/protocol/literature or a prespecified rule rather than outcome searching.

**Stage B — upstream front-end/selector evaluation with parameters frozen before ECG scoring**

Primary metrics include:

- candidate availability and explicit failure rate;
- broad physical-ROI compliance;
- winner-versus-runner-up score margin / target confidence;
- block-local target trajectory continuity without optimizing switch count;
- implausible target jumps in bins/meters per unit time;
- phase stability / circular dispersion / unwrap-jump rate;
- dynamic-to-static or target-to-background contrast;
- neighborhood/channel consistency;
- agreement with independently synchronized posture/motion evidence when available, e.g. RGB head/body motion.

**Stage C — frozen-path held-out physiology validation**

After the candidate method and selector/path are frozen, participant-held-out ECG/RSP validation should report HR/BR MAE, median AE, bias, Bland-Altman limits, coverage/failure and participant/session distributions. Correlation is secondary.

A bounded study was recommended: current baseline + at most two physically justified/reusable candidates, with prespecified decision rules.

#### 8. Distance gate / physical ROI

The assistant corrected the earlier over-broad “physical gate unresolved” wording.

The new distinction is:

**Broad physical ROI — recommended and likely necessary.**

Use independent geometry and protocol facts such as radar installation position/orientation, chair/participant chest region, room dimensions, wall/adjacent-room geometry, calibrated bin spacing/range bias, sensor useful range/FOV, posture/slouch/reposition tolerance. This ROI should contain every physically plausible participant position while excluding impossible regions such as >10 m, behind walls or another room.

**Narrow physiology-valid gate — still unresolved.**

The historical 0.30–1.50 m interval remains:

```text
HISTORICAL_GATE_SENSITIVITY
```

and should not be described as a validated physiology gate unless supported by independent placement/calibration evidence rather than HR error.

Issue #26/T2 was assigned to recover geometry and freeze either a defensible coarse physical ROI or the precise remaining missing physical facts.

#### 9. 20 s versus 60 s window comparison

The assistant corrected an earlier interpretation that the existing comparison was invalid because selector/path differed.

The canonical correction states that the existing 20 s versus 60 s comparison is a legitimate **controlled diagnostic duration comparison** because it fixed the historical target and reused the same v3.1.1 bandpass/periodogram/peak/course chain while changing the trailing duration.

The reported descriptive result remains:

- 20 s MAE: ~14.703 bpm.
- 60 s MAE: ~5.609 bpm.
- 283 common ECG-valid pairs: 60 s better in 208, 20 s better in 74, one tie.

However, 20 s originally entered as a block-local continuity/ECG-alignment engineering diagnostic (`20 s window / 10 s step / 5 s boundary guard`) without a physiological argument that it was an optimal HR window.

The status was therefore frozen as:

```text
20S = HISTORICAL_DIAGNOSTIC_ONLY
```

The assistant also separated historically different temporal contracts that had previously been conflated:

- 25 s: internal v3.1.1 HR time-course estimation window.
- 40 s with 20 s step: VMD decomposition window/step.
- 60 s: historical trailing probe-level HR aggregation.
- `pre_30s`: canonical multimodal probe-alignment window, not automatically the internal physiological estimator duration.

T4 was assigned to reconcile the final HR/BR temporal contract only after selector/path and physical ROI are frozen.

#### 10. HRV and proving `radar beat ≈ ECG R-peak`

The assistant explained that average HR agreement is insufficient for HRV; beat timing must be validated.

The formal beat-level logic was described as:

1. synchronize formal blocks using experiment markers, Biopac digital pulses and audited mmWave Unix timestamps, retaining alignment residuals;
2. detect ECG R-peaks independently with ECG detector/QC;
3. generate radar beat timestamps blind to ECG peak timing;
4. perform one-to-one matching with a prespecified primary tolerance, currently ±75 ms, and a wider ±150 ms sensitivity analysis; no beat can be reused;
5. report TP/FN/FP, sensitivity/recall, precision, F1, timing bias, median absolute timing error and p95 timing error by participant/block/window;
6. form paired consecutive intervals only when adjacent radar beats and ECG R-peaks are both validly matched; compare radar IBI to ECG R-R interval using coverage, MAE/bias and Bland-Altman;
7. inspect missed beats, extra peaks, harmonic locking, synchronization errors and weak-signal intervals;
8. calculate RMSSD/SDNN only after a prespecified beat-level gate passes.

Current FocusWave evidence discussed:

- ±75 ms: sensitivity ~0.170, precision ~0.211.
- ±150 ms: sensitivity ~0.359, precision ~0.444.
- per-window median paired-IBI MAE ~46.258 ms.
- same-window beat-derived mean HR versus spectral HR median absolute difference ~49.114 bpm.

Thus the state remained:

```text
HRV/IBI = BLOCKED / EXCLUDE
```

The assistant also noted the conventional ~5 min short-term HRV reference and that ultra-short HRV exists but requires metric- and context-specific validation rather than assuming that an HR window such as 20 s is suitable for HRV.

#### 11. GitHub changes and task assignment

The assistant directly changed `requirements.txt` on `main` from:

```text
vmdpy>=0.2
```

to:

```text
sktime==1.1.0
```

in commit:

```text
7513dbe9d7c2fe0d168bb70cffd88de855965924
fix(mmwave): pin maintained sktime VMD backend
```

A detailed canonical correction document was added:

```text
docs/canonical/MMWAVE_FRONTEND_DATA_DOMAIN_AND_VALIDATION_DECISION_2026-08-30.md
```

in commit:

```text
ed50b14fe596b2d58f3884d267b290dc4ea96366
docs(mmwave): correct frontend data-domain and validation roadmap
```

The assistant explicitly did **not** claim that source-level VMD closure was complete, because the large producer still contained the historical `_load_vmd()` fallback.

The task map frozen through the last mmWave-specific step before multimodal integration was:

- **T0 / #29** — local Codex reproducibility closure: remove `_load_vmd()` standalone fallback, enforce exact `sktime==1.1.0`, persist VMD software/parameter provenance, add tests, isolated old-vs-new parity/smoke audit, delete the truly redundant `codex/mmwave-production-contract-review-fix-v1` remote ref, keep PR #20 closed/unmerged/[SUPERSEDED].
- **T1 / #27** — acquisition/data-domain + historical preprocessing provenance audit.
- **T2 / #26** — independent coarse physical ROI contract.
- **T3 / #27** — bounded baseline + at most two physics-compatible reusable front-end/selector candidates, parameter-frozen before physiological scoring.
- **T4 / #25** — formal HR/BR temporal-window contract after selector/path + ROI freeze; 20 s remains diagnostic history.
- **T5 / #29 supervision** — participant-held-out HR/BR validity gate against ECG/RSP.
- **T6 / #29 supervision** — beat/HRV validity gate; HRV remains excluded unless beat timing passes.
- **T7 / #29 supervision** — mmWave probe adapter to canonical 1,440-probe timeline with explicit missingness, schema validation and canonical 5-column key. T7 PASS is the last mmWave-specific step before final multimodal attach/contribution analysis.

---

## Turn 3 — User

> 字太小而且解释地不详细，不要放在一张图里，只放又必要用图解释的

---

## Turn 4 — Assistant

**Transcript event:** the assistant attempted additional image generation rather than continuing only in text. The user then rejected image generation. These generated images are intentionally not embedded in this Markdown archive.

---

## Turn 5 — User

> 不要生成图片了呀。。。我让你做的事情，都做了嘛？查的都查了嘛，和我解释。同步完了吗，记录完整吗

---

## Turn 6 — Assistant

The assistant first acknowledged the constraint and switched to repository-state verification:

> 不会再生成图片。我现在只核对 GitHub 真实状态：`main` 最新 HEAD、VMD 代码是否真的全部改完、canonical 记录是否完整、#25/#26/#27/#29 的任务是否都已同步，然后明确告诉你“已完成 / 未完成 / 还缺什么”，不含糊。

After rechecking GitHub, the assistant reported a completion-boundary correction:

> 核验到一个必须明确告诉你的事实：**不是“所有事情都已经做完”。** 文档/任务同步基本完整，但执行层还剩几项真实未完成：`_load_vmd()` 仍有 `sktime → vmdpy` fallback；重复分支仍然存在；ADC→NPZ 的上游采集/Range-FFT 配置历史还没有完成 T1 追溯；距离 coarse ROI、最终 selector A/B、正式窗口、held-out HR/BR、beat-level HRV、probe adapter 都还是后续执行任务。我要把这个“完成/未完成边界”也写回 #29，避免 GitHub 上出现“看起来已经全部闭环”的错觉。

### Final status explanation to the user

> 没有全部“执行完成”。我刚刚重新逐项核验了一遍，现在可以把边界说清楚：**你这轮要求我查清、解释清、纠正分析方向、同步 GitHub、安排后续任务——这些已经基本完成；但真正需要本地代码执行/数据复跑的部分并没有假装成已完成。** 我也已经把这个“哪些完成、哪些没完成”的边界追加写进了 GitHub Issue #29，避免后面的 AI 又把“已规划”误读成“已执行”。

The assistant then summarized the verified state:

| 项目 | 真实状态 |
|---|---|
| VMD 正式 backend 决策 | **已完成**：`sktime.libs.vmdpy.VMD`，锁 `sktime==1.1.0` |
| `requirements.txt` | **我已经直接修改并提交** |
| `_load_vmd()` 删除 `sktime → vmdpy` fallback | **还没执行**，已布置给本地 Codex |
| DC offset 原理、为什么影响 phase | **已查文献、已解释、已同步** |
| ADC vs range-domain DataCube | **概念和当前 producer 数据域已查清并同步** |
| 当前 NPZ 是否还能做 ADC-level Hamming 等 | **边界已查清**：不能直接重做；但上游当年到底用了什么还要 T1 追溯 |
| Hamming / Blackman-Harris 原理 | **已查官方 TI 文档并同步** |
| 335-window mean subtraction 结果重新解释 | **已纠正并同步**：切换率↑不能直接叫“恶化” |
| 历史是否尝试过其他处理 | **已查到确实有很多历史探索**；但完整逐方法 provenance matrix 尚待 T1 |
| 如何选择 preprocessing，而不是只看 HR MAE | **方法学已经冻结并同步** |
| 是否需要距离 gate | **已纠正**：需要 broad physical ROI；0.30–1.50 m 暂不能当正式 physiology gate |
| 20 s 的来源 | **已查清**：工程 diagnostic，不是正式生理窗口依据 |
| 20 s vs 60 s 对比是否完全错误 | **已纠正**：并非完全错误，是受控 diagnostic comparison，但不能据此直接定正式窗口 |
| HRV 为什么不能直接做 | **已查标准和 ultra-short 文献；beat-level gate 已定义** |
| 下一步直到多模态前的任务 | **T0–T7 已全部分配到现有 Issue** |
| 重复 branch 删除 | **尚未删除**，还真实存在；已放进 T0 |
| PR #20 | **已关闭、未合并、标记 SUPERSEDED**，保留历史 provenance |
| 最终 mmWave 多模态 adapter | **尚未执行，T7** |

The assistant verified that `main` was:

```text
ed50b14fe596b2d58f3884d267b290dc4ea96366
docs(mmwave): correct frontend data-domain and validation roadmap
```

### VMD correction boundary

The assistant explicitly corrected the earlier shorthand “已经改了”:

> **我只已经直接改完了 dependency 文件，还没有改完 producer。**

`requirements.txt` was verified as containing `sktime==1.1.0`, and commit `7513dbe...` was verified to change only:

```diff
-vmdpy>=0.2
+sktime==1.1.0
```

But the current producer still contained:

```python
def _load_vmd():
    try:
        from sktime.libs.vmdpy import VMD
        return VMD, "sktime.libs.vmdpy"
    except Exception:
        from vmdpy import VMD
        return VMD, "vmdpy"
```

Therefore the true state was stated as:

> **依赖规范已由我提交修正；producer 源码和 tests 的闭环由 T0 本地 Codex 执行。**

### Literature / method verification summary

The assistant reiterated that DC-offset claims were grounded in peer-reviewed FMCW/mmWave vital-sign literature, including the distinction between simple mean subtraction and broader geometric/dynamic DC calibration.

The ADC/DataCube boundary was reiterated with TI processing documentation: ADC samples are Range-FFT transformed into a radar cube; current FocusWave archived producer inputs are range-domain complex arrays, so fast-time windowing cannot simply be replayed on the existing NPZ.

The 335-window result was formally restated as **ambiguous with respect to switching correctness**, not proven degradation.

Historical method exploration was confirmed but a complete method-by-method provenance audit remained T1.

The front-end method-selection policy was restated: physics/data-domain validity first, non-ECG upstream metrics second, then held-out ECG/RSP validation after parameters/path are frozen.

The distance-gate correction was restated as broad physical ROI recommended, narrow 0.30–1.50 m physiology gate unresolved.

The 20 s correction was restated as `HISTORICAL_DIAGNOSTIC_ONLY`; the 20-versus-60 result remains evidence but is not itself production-window promotion.

HRV remained blocked at the beat-level matching gate.

### GitHub record completeness

The assistant characterized the current documentation state as:

```text
DOCUMENTATION_SYNC = PASS
```

for the facts, corrections and decisions already established in this conversation, centered on:

```text
docs/canonical/MMWAVE_FRONTEND_DATA_DOMAIN_AND_VALIDATION_DECISION_2026-08-30.md
```

The canonical governance rule was noted: future changes to input-domain interpretation, ROI/gate, front-end candidate, selector/path, window contract, beat gate, VMD backend or multimodal eligibility must be written to canonical GitHub state in the same mainline cycle; chat-only decisions are non-authoritative.

The assistant also added a completion-boundary audit comment to Issue #29 so that planned/assigned work could not be mistaken for completed execution.

### Explicit remaining incompletions

The assistant identified three broad classes that must not be presented as complete:

1. VMD producer source patch and tests are not yet complete; `_load_vmd()` fallback still exists.
2. T1 upstream acquisition provenance is not yet complete, so RS6240 raw-ADC retention, exact Range-FFT window and acquisition-side DC/IQ calibration remain unresolved.
3. The mmWave scientific pipeline itself is not final; T2–T7 still require execution: physical ROI, bounded front-end comparison, temporal contract, held-out HR/BR, beat/HRV gate and probe adapter.

The redundant branch was rechecked and confirmed to still exist:

```text
codex/mmwave-production-contract-review-fix-v1
```

at `fc682b491fcbeeb9bd1b030c8af9da33282d2846`, while PR #20 was verified closed, unmerged and `[SUPERSEDED]`.

---

## Turn 7 — User

> 把本次对话上传完整全部对话，md格式，存到github

---

## Turn 8 — Assistant action

The assistant created this Markdown archive in the canonical mmWave repository on `main`.

Path:

```text
docs/conversations/2026-08-30_mmwave_methodology_validation_full_conversation.md
```

This archive intentionally preserves the user-visible technical discussion and decision history while excluding hidden internal reasoning/tool traces.
