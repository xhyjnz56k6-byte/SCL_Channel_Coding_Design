# Stage11 命令

```powershell
python Task/CC/simulation/stages/S3/stage11_soft_quantization/scripts/run_stage11.py --clean
python Task/CC/shared/scripts/cc_stage_audit.py Task/CC/simulation/stages/S3/stage10_traceback_study/manifest.json
git diff --check
```
