# 实际命令

```powershell
cmake -S Task/BCH/simulation/current -B Task/BCH/simulation/build/s6_stage02_metrics_mingw -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build Task/BCH/simulation/build/s6_stage02_metrics_mingw --config Release --parallel 1
ctest --test-dir Task/BCH/simulation/build/s6_stage02_metrics_mingw -C Release --output-on-failure
```
