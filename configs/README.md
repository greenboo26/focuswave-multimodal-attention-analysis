# 当前分析阶段路径配置

当前正式分析阶段使用以下稳定位置：

- 校准和同步数据：`D:\acq_mmwave_data`
- 预实验数据：`I:\预实验`
- 项目派生数据：`D:\Project\厚粲杯\11_数据`
- 正式实验数据：位于移动硬盘，盘符可能变化

主线脚本应通过 `scripts/path_registry.py` 读取路径，不要在新代码中继续写入历史路径 `E:\Data`、`F:\预实验`、`J:\预实验` 或旧的正式实验路径。

## 本机配置

复制 `paths.example.json` 为 `paths.local.json`，填写正式数据移动硬盘当前路径。`paths.local.json` 已被 Git 忽略，不会上传到 GitHub。也可以设置环境变量：

```powershell
$env:FOCUSWAVE_FORMAL_DATA_ROOT = 'M:/正式实验'
```

检查路径：

```powershell
python scripts/path_registry.py --check
```

正式数据路径为空时，检查程序会报告警告，但不会把校准、预实验和项目派生数据判为缺失。
