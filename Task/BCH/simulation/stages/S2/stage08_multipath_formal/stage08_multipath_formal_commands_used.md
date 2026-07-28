# stage08_multipath_formal 执行命令

```text
cmake -S Task/BCH/simulation/stages/S2/stage08_multipath_formal/cpp -B Task/BCH/simulation/stages/S2/stage08_multipath_formal/build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build Task/BCH/simulation/stages/S2/stage08_multipath_formal/build --config Release -j 4
stage08_multipath_formal_runner.exe --self-test stage08_multipath_formal_frozen_grid.csv
stage08_multipath_formal_runner.exe GRID CHECKPOINT_TEST_RESULT 5fb6a37... CONFIG_HASH 0 24 2500
stage08_multipath_formal_runner.exe GRID CHECKPOINT_TEST_RESULT 5fb6a37... CONFIG_HASH 0 24
stage08_multipath_formal_runner.exe GRID CONTINUOUS_TEST_RESULT 5fb6a37... CONFIG_HASH 0 24
stage08_multipath_formal_runner.exe GRID SHARD_0_RESULT 5fb6a37... CONFIG_HASH 0 2
stage08_multipath_formal_runner.exe GRID SHARD_1_RESULT 5fb6a37... CONFIG_HASH 1 2
python stage08_multipath_formal_process.py
python stage08_multipath_formal_check.py
python stage08_multipath_formal_plot.py
python stage08_multipath_formal_plot_check.py
git diff --check
git commit -m "BCH/stage08：实现多径正式仿真与分片运行器"
git commit -m "BCH/stage08：补全帧级检查点与正式结果检查"
git commit -m "BCH/stage08：完成多径正式数据与科研绘图"
git push origin stage07-08-bch-s2-multipath
```

两个正式 shard 并行运行，使用互斥 grid 行；首轮 `e055724...` 数据没有进入
最终结果。最终数据记录 `gitCommit=5fb6a373263eb6a50d0ef70a14cad16963a0fb3d`，
`configHash=457ea7422976679d98dd9ca6857c00c84e2fbb71e546f759d4ff745aac299a84`。
