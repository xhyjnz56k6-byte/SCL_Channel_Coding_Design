# Stage04 命令

```powershell
python Task/CC/simulation/stages/S3/stage04_soft_viterbi/scripts/build_and_test_stage04.py --clean
matlab -batch "run('.../stage04_soft_viterbi/matlab/stage04_matlab_reference.m')"
git diff --check
```
