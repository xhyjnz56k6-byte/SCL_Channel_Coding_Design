# Common-04 Commands Used

```text
python Task/Common/scripts/build_common04.py
Task/Common/build/stage04/test_common04_random_policy.exe
Task/Common/build/stage04/test_common04_gaussian_noise.exe
Task/Common/build/stage04/test_common04_modulation_awgn.exe
Task/Common/build/stage04/test_common04_metrics_control.exe
Task/Common/build/stage04/test_common04_checkpoint.exe
Task/Common/build/stage04/test_common04_integration.exe
python Task/Common/scripts/check_common02.py
python Task/Common/scripts/check_common03.py
python Task/Common/scripts/check_common04.py
python Task/Common/scripts/compare_common04_cpp_python.py
python Task/Common/scripts/merge_common04_shards.py
```

The Common-04 checker generates temporary Common-03 frame pools and Common-04 noise pools under `Task/Common/build/stage04/`, executes pool-backed smoke and prescan, then validates CSV, metadata, PNG, source scope, acceptance, manifest, and regressions.
