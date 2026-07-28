# Stage01 执行命令

以下命令从仓库根目录执行；具体返回码和结果在 `validation_report.md` 中记录。

```powershell
python Task/CC/simulation/stages/S3/stage01_cc_contract/tests/test_stage01_contract.py
python Task/CC/simulation/stages/S3/stage01_cc_contract/scripts/check_stage01_contract.py
git diff --check
git status --short
git diff --name-only
```
