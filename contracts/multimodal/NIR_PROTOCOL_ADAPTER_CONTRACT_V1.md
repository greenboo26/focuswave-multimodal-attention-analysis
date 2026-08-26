# NIR site/protocol adapter contract V1

状态：`ACTIVE / REQUIRED_WHEN_EXTERNAL_RUNTIME_PROTOCOL_DIFFERS`

本 contract 适用于中央仓库与外部 `kyandi233-dev/Attention-Analysis` NIR producer 的跨 site/protocol 运行。它不要求现在创建一个虚构的珠海配置；它规定：当实际数据协议与外部 runtime 当前 frozen config 不一致时，什么才算一个可被批准的 adapter/config。

## 1. 触发条件

只要外部 NIR runtime 的当前 config 与实际 session 在以下任一项不一致，就必须触发 adapter review：

- 正式 block 数；
- block/phase 名称或顺序；
- baseline/instruction/practice 边界；
- probe 数量或 probe event 语义；
- master timeline event 命名/单位；
- 正式 session inclusion rule；
- site-specific data layout 对 phase discovery 有影响。

当前已知外部 AMD `runtime/nir-formal/config.yaml` 是 v3.1.3、两个正式 B block 的 scope，因此不得自动假设适用于三 block/BBB session。

## 2. Adapter 可以改什么

在不创建新 NIR 科学版本的前提下，site/protocol adapter 可以只处理：

- 数据根/文件发现；
- session naming；
- phase/timeline event 映射；
- block 数和每个 block 的实际时间边界；
- probe/timeline bridge；
- output 中 site/protocol provenance 字段。

## 3. Adapter 不能偷偷改什么

若要修改以下任一项，必须创建新的 NIR pipeline/version 并单独科学 review，而不是称为“协议适配”：

- YOLO/RITnet 模型或权重；
- input geometry；
- detector threshold/NMS；
- ROI expansion；
- pupil/segmentation metric 定义；
- QC threshold；
- frame sampling/跳帧规则；
- tracking policy；
- downstream label/window/model/fold；
- outcome-dependent filtering。

## 4. Adapter 必须来自实际数据证据

Adapter 不能根据登记表或记忆直接编写。至少需要从实际挂载数据核验：

1. formal session 列表；
2. behavior 文件数量与 Block 字段；
3. master timeline 的 phase marker；
4. 每 Block probe 数及绝对时间戳；
5. NIR video 的 session 对应关系；
6. 缺失/异常 session。

若 session 之间协议不一致，不能用一个 config 静默覆盖全部；必须明确 cohort/subset 或建立显式版本映射。

## 5. 最低 provenance

每个 approved adapter/config 必须保存：

- `site`；
- `protocol_id`；
- adapter/config version；
- source evidence summary；
- external `Attention-Analysis` exact commit；
- external runtime package version；
- config SHA256；
- model SHA256；
- expected block/phase/probe structure；
- exceptions/exclusions；
- reviewer/date。

## 6. Preflight acceptance

正式全量 NIR production 前，至少在 1 个完整代表性 session 上验证：

- phase windows 全部存在且顺序正确；
- 所有正式 blocks 被覆盖，不多不少；
- Probe/timeline 时间轴与 behavior 一致；
- video frame/time coverage 与 phase windows 有合理交集；
- completion/run manifest 记录正确 protocol/site/config；
- 没有因为新增 block 而改变 detector/segmentation/QC 科学定义。

建议再选择一个边界/异常 session 做第二个 preflight，以确认 adapter 不只对单个“最干净”session 有效。

## 7. Fail-closed 规则

出现以下情况必须停止 formal batch：

- 实际三 Block，但 config 只识别两 Block；
- timeline 缺失导致无法确定 Block 边界；
- 同一 session 存在多个冲突视频；
- Probe 时间与 phase windows 明显不一致；
- adapter 需要根据 outcome/label 才能决定怎么切片；
- external runtime/model/config provenance 无法确定。

允许输出 audit，不允许把失败的 preflight 升级为 formal result。

## 8. 与中央分析的关系

NIR adapter 解决的是“把实际 NIR 原始数据按正确协议生产成统一 derived/QC”的问题，不负责最终 statistical inference。

通过 adapter gate 后，外部 producer 的标准化派生结果再进入中央：identity reconciliation → canonical cohort → participant-disjoint folds → multimodal/final inference。

因此 site 数据数量不同不是失败；scientific definition 不一致才是失败。

## 9. 当前裁决

在实际三 Block/BBB 数据尚未完成本 contract 所要求的 protocol audit 前，不创建一个猜测性的“珠海正式 config”。当前正确状态是 `ADAPTER_REQUIRED_IF_BBB_CONFIRMED`，而不是假装已经支持。