# VS_DATASET 完整数据获取核查

日期：2026-08-25  
范围：只读核查数据入口、本地存在性和访问条件；未运行算法，未上传被试级数据。

## 结论

正式 VS_DATASET benchmark 所需的完整 24 被试 Radar–Mindray 参考数据目前未在本地工作区中确认到。公开入口已经确认存在，因此当前状态不是“数据集不存在”，而是“完整数据包尚未下载到本地”。

## 缺失资产

官方 README 列出的完整包应包含：

- `VS01`–`VS24` 共 24 名被试；
- 每名被试的 `Resting.mat`、`Resting_Mindray.mat`、`Apnea.mat`、`Apnea_Mindray.mat`；
- `Subject Information.xlsx`；
- 与正式 benchmark 相关的来源、许可/使用条款和下载后哈希清单。

## 已确认入口

1. 官方说明页：<https://github.com/Rc-W024/VS_DATASET/blob/main/HEALTHY.md>
2. IEEE DataPort：<https://doi.org/10.21227/wq68-sv85>
3. Catalan Open Research Area 备用入口：<https://doi.org/10.34810/data2962>
4. 官方代码与示例仓库：<https://github.com/Rc-W024/VitalSense2024>

官方说明页写明完整包约 31 MB，并列出 24 个被试目录和 Mindray 配套文件；官方 VitalSense2024 README 将仓库内 `data` 定义为 sample data，用于测试、熟悉和算法研究，不能替代完整健康队列。

## 本地检查

检查范围：

- `D:\Project\厚粲杯\08_算法`
- `D:\Project\厚粲杯\11_数据`
- `D:\Project\厚粲杯\11_数据\derived`

未发现名为 `VITALSENSE_120_DATASET` 的完整数据包，也未发现成套 `VS01`–`VS24` 与 `*_Mindray.mat` 文件。该检查不改变任何文件。

## 访问与许可边界

官方 README 明确给出 IEEE DataPort 和备用数据仓库入口。当前尚未把数据集页面上的具体下载条款或数据许可单独核验为可直接复述的许可结论，因此下载时必须保存页面上的实际条款；代码仓库的 MIT 标识不能自动推定原始数据采用 MIT 许可。

## 下一步

通过两个数据入口之一取得完整包后，记录：下载页面、下载日期、许可/使用条款、文件数量、文件大小、SHA-256 和 subject/session manifest。完成这些记录后再恢复冻结的 C1b benchmark；在此之前不把 VitalSense 示例 smoke test 当作性能证据。
