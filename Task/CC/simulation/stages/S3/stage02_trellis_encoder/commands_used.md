# Stage02 命令

```powershell
python Task/CC/simulation/stages/S3/stage02_trellis_encoder/scripts/build_and_test_stage02.py --clean
matlab -batch "run('Task/CC/simulation/stages/S3/stage02_trellis_encoder/matlab/stage02_matlab_reference.m')"
git diff --check
```
