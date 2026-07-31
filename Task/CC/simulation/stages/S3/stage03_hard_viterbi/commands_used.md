# Stage03 命令

```powershell
python Task/CC/simulation/stages/S3/stage03_hard_viterbi/scripts/build_and_test_stage03.py --clean
matlab -batch "run('.../stage03_hard_viterbi/matlab/stage03_matlab_reference.m')"
python Task/CC/simulation/stages/S3/stage02_trellis_encoder/scripts/build_and_test_stage02.py
git diff --check
```
