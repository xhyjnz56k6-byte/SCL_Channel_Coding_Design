# 实际执行命令

```text
cmake -S Task/BCH/segmented/current -B Task/BCH/segmented/build/bch04 -G "MinGW Makefiles"
cmake --build Task/BCH/segmented/build/bch04 --config Release
ctest --test-dir Task/BCH/segmented/build/bch04 --output-on-failure
Task/BCH/segmented/build/bch04/test_bch15_lookup_decoder.exe <stage> <seed-fixture>
python Task/BCH/segmented/scripts/check_bch04_lookup_decoder.py <stage>
git diff --check
```

六项 Common 二进制回归实际执行：`test_common04_random_policy.exe`、`test_common04_gaussian_noise.exe`、`test_common04_modulation_awgn.exe`、`test_common04_metrics_control.exe`、`test_common04_checkpoint.exe`、`test_common04_integration.exe`。
