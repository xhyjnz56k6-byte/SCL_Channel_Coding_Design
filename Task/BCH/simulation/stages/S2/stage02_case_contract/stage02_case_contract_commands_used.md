# stage02_case_contract 实际命令

```powershell
python Task/BCH/simulation/stages/S2/stage02_case_contract/python/stage02_case_contract_run.py
python Task/BCH/simulation/stages/S2/stage02_case_contract/python/stage02_case_contract_check.py
```

运行器实际执行 Release CMake/MinGW 构建、CTest、C++ 契约导出、MATLAB R2024b
独立长度/码率复算和 Python 业务 checker。

修复记录：

1. 首次 CTest 因被引用子工程注册未构建的历史测试而失败，改为只链接所需源码库；
2. MATLAB 列名自动识别失败，改为按冻结 schema 读取；
3. `displayName` 中逗号使未转义 CSV 错列，名称改为无逗号的简短唯一文本；
4. MATLAB 自动把 `|` 识别为分隔符，显式冻结逗号为 CSV 分隔符；
5. MATLAB 把多值向量列推断为数值并产生 missing，显式冻结这些列为 string；
6. 第六次从构建到 checker 完整重跑通过。

任一失败后均未进入 stage03。
