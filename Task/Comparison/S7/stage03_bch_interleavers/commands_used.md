# Stage03 命令

```text
cmake -S Task/Comparison/S7 -B Task/Comparison/S7/build/stage03_09 -G "MinGW Makefiles"
cmake --build Task/Comparison/S7/build/stage03_09 --parallel 2
ctest --test-dir Task/Comparison/S7/build/stage03_09 --output-on-failure
```

