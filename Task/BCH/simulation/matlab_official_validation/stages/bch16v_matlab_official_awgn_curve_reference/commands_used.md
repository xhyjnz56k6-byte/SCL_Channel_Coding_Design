# BCH-16V commands used

```text
git fetch origin
cmake -G "MinGW Makefiles" -S Task/BCH/simulation/matlab_official_validation -B Task/BCH/simulation/matlab_official_validation/build_mingw
cmake --build Task/BCH/simulation/matlab_official_validation/build_mingw --target bch16v_export_shared_input -j 4
python Task/BCH/simulation/matlab_official_validation/scripts/run_bch16v.py --dry-run --progress
python Task/BCH/simulation/matlab_official_validation/scripts/run_bch16v.py --all --progress
python Task/BCH/simulation/matlab_official_validation/scripts/run_matlab_parallel.py --matlab D:/Apps/Matlab/bin/matlab.exe --matlab-dir Task/BCH/simulation/matlab_official_validation/matlab --runtime-config Task/BCH/simulation/matlab_official_validation/results/runtime_config.json --input-manifest Task/BCH/simulation/matlab_official_validation/input/shared_payload_noise/shared_input_manifest.json --results-dir Task/BCH/simulation/matlab_official_validation/results/matlab_official --workers 4
python Task/BCH/simulation/matlab_official_validation/scripts/run_bch16v.py --compare-only
python Task/BCH/simulation/matlab_official_validation/scripts/run_bch16v.py --plot-only
python Task/BCH/simulation/matlab_official_validation/scripts/run_bch16v.py --audit-only
```

历史回归实际命令：

```text
ctest --test-dir Task/Common/build/stage04 --output-on-failure
ctest --test-dir Task/BCH/segmented/build/bch02_encoder --output-on-failure
ctest --test-dir Task/BCH/segmented/build/bch03 --output-on-failure
ctest --test-dir Task/BCH/segmented/build/bch04 --output-on-failure
ctest --test-dir Task/BCH/segmented/build/bch05_adapter_recovery --output-on-failure
ctest --test-dir Task/BCH/segmented/build/bch06_segmented_matlab_reference/cmake --output-on-failure
ctest --test-dir Task/BCH/block/build/group3 --output-on-failure
ctest --test-dir Task/BCH/simulation/build/current --output-on-failure
python Task/BCH/segmented/scripts/run_bch06_segmented_matlab_reference.py --repo-root . --build-dir Task/BCH/segmented/build/bch16v_regression_bch06 --matlab-command D:/Apps/Matlab/bin/matlab.exe
python Task/BCH/block/scripts/run_bch_group3.py --all --matlab-command D:/Apps/Matlab/bin/matlab.exe --build-dir Task/BCH/block/build/bch16v_regression_group3
```

大型共享输入不提交；一键复现入口保持为：

```text
python Task/BCH/simulation/matlab_official_validation/scripts/run_bch16v.py --all --progress
```

