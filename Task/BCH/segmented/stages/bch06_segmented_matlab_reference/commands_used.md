# BCH-06 commands used

python Task/BCH/segmented/scripts/run_bch06_segmented_matlab_reference.py --repo-root . --build-dir Task/BCH/segmented/build/bch06_segmented_matlab_reference --matlab-command D:/Apps/Matlab/bin/matlab.exe
python Task/BCH/segmented/scripts/generate_bch06_audit.py
git diff --check
Task/Common/build/stage04/test_common04_random_policy.exe
Task/Common/build/stage04/test_common04_gaussian_noise.exe
Task/Common/build/stage04/test_common04_modulation_awgn.exe
Task/Common/build/stage04/test_common04_metrics_control.exe
Task/Common/build/stage04/test_common04_checkpoint.exe
Task/Common/build/stage04/test_common04_integration.exe
git diff --name-only main...HEAD -- Task/Common
git diff --name-only main...HEAD -- Task/BCH/segmented/stages/bch01_...bch05_
git diff --name-only main...HEAD -- Task/BCH (BCH-07 range filter)
