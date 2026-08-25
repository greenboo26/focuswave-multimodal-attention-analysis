# 信效度与系统验证：调研结论及报告策略

日期：2026-08-25

## 1. 目的与结论

本文件用于确定厚粲杯报告中“信度与效度”部分的科学写法，避免两种相反问题：一是把传统心理量表的信度指标机械套用到传感器和算法；二是为了显得完整而堆叠过多验证层级、造成主线分散。

综合数字测量、thought probe、雷达心脏测量和预测模型报告规范后，建议正文只保留三条主证据链：

1. **注意状态标签的构念有效性**：thought probe 是否与行为、任务时间进程及必要的问卷指标呈现理论一致关系；
2. **毫米波测量与算法的可靠性/有效性**：项目数据质量控制 + 独立公开 Radar–ECG 数据上的算法基准验证；
3. **最终识别系统的泛化与增量有效性**：在未见参与者上验证模型，并检验毫米波相对于时间/区组与行为基线是否增加有效信息。

其余项目，例如完整可用性验证、复杂重复测量一致性、每个雷达特征逐一做生理效度、全面亚组验证等，不作为当前比赛报告正文的必需项；必要时放入附录或后续研究。

## 2. 为什么采用三条主证据链

验证—分析验证—临床验证框架（verification, analytical validation, and clinical validation [V3]）将传感数字测量的证据区分为传感器是否按规格工作、算法是否能正确得到目标生理/行为量，以及最终数字测量在具体使用情境中是否具有意义。该框架最初用于数字医学，但作者明确指出其术语和思路也可指导其他数字测量工具。2025 年的 V3+ 扩展又加入可用性验证，但可用性并不需要成为本项目当前科研报告的主分析层级。

美国食品药品监督管理局（U.S. Food and Drug Administration [FDA]）2026 年关于数字衍生测量的文件进一步强调：技术是否“适合用途”取决于测量对象、目标人群和使用情境；验证证据必须与实际声称相匹配。这一点对本项目尤其重要：如果我们声称“毫米波算法可以从雷达信号恢复逐搏/心搏间期”，需要参考测量；如果只把某些原始毫米波特征作为预测输入，则不需要逐个赋予生理含义。

Daniore 等（2024）关于可穿戴数字生物标志物开发的框架还强调两个与本项目直接相关的原则：数据聚合时间尺度应由研究问题决定，且内部个体基线与外部基准可以承担不同作用。这支持我们将静息/休息用于个体基线和反应性分析，而不是把所有生理数据都压成固定 60 s 均值。

## 3. 主证据链一：注意状态标签的构念有效性

### 3.1 当前标签的科学命名

当前四类 thought probe 为：

1. 完全专注于分拣任务；
2. 关注实验本身，但没有聚焦于分拣任务；
3. 在想与实验无关的事情；
4. 大脑空白，没有明确想法。

因此，当前 `1 vs 2/3/4` 的二元主终点只能解释为“完全任务聚焦 vs 其他非完全任务聚焦状态”，不能直接写成“专注 vs 走神”。第 3 类最接近典型任务无关思维，第 4 类属于思维空白，第 2 类是实验相关但任务未聚焦状态。

### 3.2 不应怎样做

Thought probe 测的是随时间变化的即时状态，因此不能把传统量表内部一致性或普通重测一致性当作核心信度指标。前后 probe 不一致可能是真实的状态变化，而不是测量失败。

### 3.3 正文真正需要的证据

Kane 等（2021）对 1,108 名本科生的 thought-probe 构念效度研究表明，探针方法的效度应通过它与其他理论相关变量的关系来判断，例如跨任务稳定性、执行控制表现、回顾性走神报告和 trait 问卷，而不是简单依赖一个内部一致性系数。

结合本项目，正文只需要优先建立以下两类证据：

- **行为/任务进程一致性**：probe 前错误、反应时及其变异、time-on-task、阶段/区组与 probe 状态是否呈理论一致关系；
- **问卷外部校标**：若存在与专注/持续注意直接相关的 trait 量表或自评，检验其与个体平均任务聚焦水平或 time-on-task 变化斜率的关系。

多模态生理一致性可作为补充，但不能为了“证明 probe”而循环使用最终要预测 probe 的同一模型输出。

### 3.4 问卷信度边界

- 正式多题量表：如确有多个共同测量同一构念的题项，可报告内部一致性；
- 单题“平时专注力如何”“通常可持续专注多久”：不能计算 Cronbach’s α，应作为单题 trait 指标或外部校标；
- 不为与核心构念无关的问卷额外制造信效度分析。

## 4. 主证据链二：毫米波测量与算法的可靠性/有效性

### 4.1 自有 RS6240 数据需要证明什么

项目自己的 RS6240 数据首先需要基本的技术可靠性和数据质量证据，例如：

- 时间同步/时间戳完整性；
- 数据可用覆盖率；
- target-lock 或目标距离稳定性；
- 明显运动伪影控制；
- 多通道空间一致性等现有质量控制结果。

这些证据用于说明“输入数据具备被分析的条件”，而不是证明某个心理构念。

### 4.2 哪些雷达特征必须做生理验证

只有当报告准备赋予明确生理解释时才需要严格的参考验证。例如，如果声称得到心率变异性（heart rate variability [HRV]），就必须先验证逐搏事件和心搏间期（inter-beat interval [IBI]）。

Frazao 等（2024）的雷达心脏活动综述指出，HRV 与平均心率不同，HRV 需要保留每个心搏峰在时间上的位置；仅依靠频谱峰得到平均心率的方法不适合直接用于 HRV。该综述同时指出当前文献的误差指标缺乏统一性，建议明确参考测量、误差指标和可重复的算法参数。

因此，本项目 HRV 的证据链应保持：

`Radar raw → cardiac waveform → beat timestamp → IBI → HRV`

并以心电图（electrocardiography [ECG]）逐搏时间作为参考。

原始相位、微动、质量描述符等若只作为预测特征，则无需逐个宣称它们代表某种生理机制；它们只需通过数据质量控制并在预测模型中接受严格的独立测试。

### 4.3 外部 VS_DATASET 应该加入，但名称必须准确

正式 VS_DATASET healthy cohort 到位后，应将其结果纳入报告，因为它能为逐搏/IBI/HRV 算法提供独立参考数据。建议在报告中称为：

**“独立公开 Radar–ECG 数据集上的算法外部基准验证”**。

该结果可以支持的表述是：

> 所采用的毫米波逐搏/IBI 算法在独立的同步 Radar–ECG 数据上能够以预先冻结的协议恢复心搏时间和相邻心搏间期，并达到所报告的误差与覆盖水平。

它不能单独支持以下表述：

- “本项目 RS6240 的 HRV 已被 ECG 验证”；
- “本项目所有被试的 HRV 均准确”；
- “外部数据集证明毫米波可以预测专注”；
- “外部硬件上的算法表现等价于本项目硬件上的表现”。

原因是外部数据集使用不同硬件、采集条件和被试环境。按照 V3/FDA 的 fit-for-purpose 逻辑，它更接近**算法层面的独立外部支持证据**，而不是对 RS6240 在本项目情境下的完整分析验证。若未来有本机 RS6240 与 ECG 同步采集数据，才能进一步完成设备/场景特异的参考验证。

### 4.4 外部 benchmark 正文建议只保留少量指标

正文无需堆满所有指标，建议核心表只保留：

- beat precision / recall / F1；
- beat timing error；
- IBI mean absolute error（平均绝对误差）；
- HR mean absolute error；
- RMSSD / SDNN error（若窗口长度和质量满足预先规则）；
- usable coverage。

更细的容差敏感性、失败类型和逐被试分布放附录。

当前 VitalSense2024 单记录 smoke test 只证明接口可运行，不能进入正式信效度结果。

## 5. 主证据链三：最终识别系统的泛化与增量有效性

### 5.1 最重要的不是“最高 AUC”

最终系统必须在训练时未见的参与者上测试。透明报告多变量预测模型与人工智能扩展指南（Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis + Artificial Intelligence [TRIPOD+AI]）虽然面向临床预测，但其对评估数据的核心原则可作为一般预测研究的参考：评估样本不应与训练/调参样本发生参与者重叠，且应同时报告区分能力和不确定性，而不能只给一个训练内成绩。

本项目的主预测指标可继续使用受试者工作特征曲线下面积（area under the receiver operating characteristic curve [AUC]）和平衡准确率，并报告参与者级 bootstrap 95% 置信区间（confidence interval [CI]）。如果系统最终输出概率用于实时界面，概率校准可以作为次级结果；当前不需要为了比赛报告把它提升为新的主线分析。

### 5.2 增量有效性比单独雷达分数更重要

C2 audit 已证明 time/block structural baseline 本身具有明显预测性，行为错误相关特征也具有预测性。因此最终评价必须回答：

`Time / Block → + Behavior → + Radar → + NIR` 

在完全相同的参与者分折和 probe 样本上，毫米波是否在时间/任务结构和行为之外稳定增加预测信息。

报告重点应包括：

- radar-only 相对于 time/block baseline 的差值；
- time + behavior 与 time + behavior + radar 的差值；
- 在严格共同样本上，radar / NIR / behavior / fusion 的配对差值及 CI；
- 参与者独立的测试结果。

这比把不同样本量上的 AUC 直接横向比较更能构成系统效度证据。

## 6. 最终比赛报告推荐结构

如果比赛模板标题要求写“信效度检验”，正文建议控制为三个小节，不扩展成六七个平级部分。

### 6.1 注意状态测量的构念有效性

写 thought probe 的设计依据、四类构念边界，以及 probe 与行为/time-on-task/必要问卷的理论一致性证据。

### 6.2 毫米波测量与算法的可靠性/有效性

写 RS6240 的核心数据质量证据；若 VS_DATASET 正式 benchmark 完成，则加入“独立公开数据集算法外部基准验证”表；HRV 仅在逐搏/IBI 参考验证通过后作生理解释。

### 6.3 识别系统的泛化与增量有效性

写 participant-disjoint 评估、AUC、balanced accuracy、95% CI，并重点比较时间/行为基线加入毫米波后的增量。

正文总长度建议控制在约 1–2 页；复杂 QC、逐被试 benchmark、容差敏感性和其他模型结果放附录。

## 7. 当前哪些工作是“必须”，哪些可以延后

### 正文必需/高优先级

1. 历史 session 的 probe 程序/文案一致性核验；
2. probe 与行为/time-on-task 的构念有效性证据；
3. common-subset 上的 time/behavior/radar/NIR/fusion 公平比较；
4. 参与者独立评估及不确定性；
5. RS6240 现有 QC/coverage 的报告级汇总；
6. VS_DATASET 正式数据一旦可得，运行冻结协议下的外部算法 benchmark。

### 有数据才做，不为报告硬凑

- 多题量表内部一致性；
- trait 问卷与 state 指标的跨层关系；
- resting/break 的个体基线与 recovery；
- HRV 的任务相关解释。

### 当前可延后/附录

- 完整 V3+ usability validation；
- 对每个雷达人工特征逐个做“生理效度”；
- 全套 test–retest / ICC；
- 大量亚组性能；
- teacher–student 模型的信效度扩展；
- 医疗/临床有效性表述。

## 8. 研究边界

本项目是大学生持续注意/任务聚焦监测研究与原型系统，不是医疗诊断系统。因此可以借鉴 V3、FDA 和 TRIPOD+AI 的证据分层和独立评估原则，但报告中不应声称已完成“临床验证”“医疗器械验证”或监管意义上的 fit-for-purpose 认证。

当前最合适的总证据链是：

`标签是否有构念依据 → 传感/算法是否测得可靠 → 换一个人还能否预测，并且是否增加已有行为/时间信息之外的价值`。

这三问回答充分即可构成比赛报告中主次清晰、不过度堆砌的信效度部分。

## 9. 参考文献

Bakker, J. P., Barge, R., Centra, J., Cobb, B., Cota, C., Guo, C. C., et al. (2025). V3+ extends the V3 framework to ensure user-centricity and scalability of sensor-based digital health technologies. *npj Digital Medicine, 8*, Article 51. https://doi.org/10.1038/s41746-024-01322-2

Daniore, P., Nittas, V., Haag, C., Bernard, J., Gonzenbach, R., & von Wyl, V. (2024). From wearable sensor data to digital biomarker development: Ten lessons learned and a framework proposal. *npj Digital Medicine, 7*, Article 161. https://doi.org/10.1038/s41746-024-01151-3

Frazao, A., Pinho, P., & Albuquerque, D. (2024). Radar-based heart cardiac activity measurements: A review. *Sensors, 24*(23), 7654. https://doi.org/10.3390/s24237654

Goldsack, J. C., Coravos, A., Bakker, J. P., Bent, B., Dowling, A. V., Fitzer-Attas, C., et al. (2020). Verification, analytical validation, and clinical validation (V3): The foundation of determining fit-for-purpose for biometric monitoring technologies (BioMeTs). *npj Digital Medicine, 3*, Article 55. https://doi.org/10.1038/s41746-020-0260-4

Kane, M. J., Smeekens, B. A., Meier, M. E., Welhaf, M. S., & Phillips, N. E. (2021). Testing the construct validity of competing measurement approaches to probed mind-wandering reports. *Behavior Research Methods, 53*(6), 2372–2411. https://doi.org/10.3758/s13428-021-01557-x

U.S. Food and Drug Administration. (2026). *Key considerations for the development and use of digitally derived measures for clinical investigations*. https://www.fda.gov/media/194348/download

Collins, G. S., Dhiman, P., Andaur Navarro, C. L., Ma, J., Hooft, L., Reitsma, J. B., et al. (2024). TRIPOD+AI statement: Updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ, 385*, e078378. https://doi.org/10.1136/bmj-2023-078378
