# Stage10 命令

```powershell
python Task/CC/simulation/stages/S3/stage10_traceback_study/scripts/run_stage10.py --clean
python Task/CC/shared/scripts/cc_stage_audit.py Task/CC/simulation/stages/S3/stage09_awgn_formal/manifest.json
git diff --check
```
