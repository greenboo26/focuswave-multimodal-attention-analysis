# 毫米波任务3：RS6240 + BIOPAC 机制/压力测试（暂缓）

Status: `DEFERRED_MECHANISM_ONLY`

Competition context: FocusWave / 厚粲杯心理学 × 人工智能测验产品。

## 1. 证据定位已修正

本任务原先被写成“设备匹配校准，用来最终决定 HR/BR 能否作为产品生理输出”。该定位过高，现已修正。

已核对 `kyandi233-dev/FocusWave@ecg` 的 2026-08-14~16 程序与提交：

- `02-tools/11-calibrate-mmwave-ecg.py`：静息5min → 深呼吸2min → 屏息45s → 静息5min；目的为毫米波×ECG/呼吸机制校准，观察 RSA、屏息与呼吸谐波对心跳提取的影响；
- `02-tools/12-test-breath-focus.py`：同一被试机械按键 vs 专注 SART 交替；目的为区分“任务态呼吸率锁低”究竟是算法问题还是真实专注/屏息生理现象；
- 两套程序均明确不同于正式实验；
- 这些重复 session 不能当成独立参与者来支持跨被试产品有效性。

因此，本地 RS6240 + BIOPAC 数据只承担：

- 设备同步与 marker 对齐检查；
- 明显生理操纵能否被雷达跟随；
- 深呼吸/屏息下的呼吸谐波与错误锁频机制；
- 机械按键 vs 正常专注条件下动作/呼吸混淆；
- 算法失败边界与压力测试。

它**不能单独承担**：

- HR/BR 的跨人外部有效性；
- 产品级 physiology 最终资格；
- 把多个 session 当多个独立被试的统计结论。

## 2. 为什么暂缓

当前更高价值的下一步是 `TASK2R_EXTERNAL_REFERENCE_50S_CONTINUATION.md`：

- AgeBalanced 有110个不同参与者和 ECG；
- 30/80 participant split 已建立；
- 50 s 输入可容纳 SSA `L=400`；
- 它更适合回答 HR 方法的跨人外部泛化问题。

因此本任务不再作为 Task 2 后的默认下一步。

## 3. 以后什么时候值得回来做

只有在以下情况之一成立时再启用：

1. AgeBalanced 50 s 外部验证发现某 HR 方法值得进入产品候选，需要用 RS6240 本机数据解释设备差异；
2. 正式数据出现可疑呼吸/心跳模式，需要用深呼吸/屏息实验解释失败机制；
3. 需要展示机械按键、专注、静息、深呼吸、屏息之间的信号机制证据；
4. BR 由于 AgeBalanced 无 RSP，需要本地 RSP 作为**探索性机制证据**，但仍不得夸大为跨人验证。

## 4. 若未来执行

应按 condition/segment 分层，而不是把11个目录当11个独立参与者统一算总体指标。

至少区分：

- rest；
- deep_breath；
- breath_hold；
- mechanical keypress；
- focused SART；
- 其他能从原 events/marker 可靠恢复的条件。

输出重点是：

- 是否跟随明显变化；
- 哪种条件会导致错误锁频；
- 呼吸谐波/动作伪影何时出现；
- 同一被试内条件差异；
- 对正式 FocusWave 数据解释有什么帮助。

不把其结果直接命名为“产品 HR/BR 已验证”。

## 5. 当前下一步

`DEFERRED`。先执行 AgeBalanced 50 s external method comparison；是否回来做本地机制/压力测试，由50 s结果和比赛剩余时间决定。
