# Canonical local audit entrypoints

本目录只收口事实审计入口，不包含新的科学分析。

- `audit_local_analysis_library.py`：参数化扫描 repo、derived、formal NIR、RGB 和 J 盘根目录，读取轻量 manifest/CSV schema，输出审计 JSON；不复制原始数据、不运行模型、不覆盖结果。
- `../path_registry.py --check`：检查项目登记路径是否存在。

实际科学分析入口必须先在 registry 中登记，并通过存在性、参数化 data/output root、dry-run、manifest、seed/config/code digest 和不覆盖检查后，才可升格为 canonical executable entrypoint。
