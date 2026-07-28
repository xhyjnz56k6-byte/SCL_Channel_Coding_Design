# stage01_foundation 实际命令

```powershell
python Task/BCH/simulation/stages/S2/stage01_foundation/python/stage01_foundation_run.py
python Task/BCH/simulation/stages/S2/stage01_foundation/python/stage01_foundation_check.py
```

`stage01_foundation_run.py` 实际依次执行：

```text
cmake -S <stage01 cpp> -B <Task/BCH/simulation/build/S2/stage01_foundation> -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build <build> --config Release -j 2
ctest --test-dir <build> -C Release --output-on-failure -V
stage01_foundation_export.exe <stage01 results>
matlab -batch "stage01_foundation_matlab_reference(...)"
python stage01_foundation_compare.py ...
```

MATLAB 表变量名接口在前两次执行中失败。修复为字符向量元胞数组后，第三次从
Release 构建、CTest、导出、MATLAB 到比较完整重跑并通过。
