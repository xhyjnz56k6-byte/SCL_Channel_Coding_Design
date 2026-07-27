# stage07_multipath_validation 执行命令

```text
git fetch origin
git worktree add C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_multipath -b stage07-08-bch-s2-multipath origin/bch-s2-stage01-02-base
git push -u origin stage07-08-bch-s2-multipath
cmake -S Task/BCH/simulation/stages/S2/stage07_multipath_validation/cpp -B Task/BCH/simulation/stages/S2/stage07_multipath_validation/build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build Task/BCH/simulation/stages/S2/stage07_multipath_validation/build --config Release -j 4
ctest --test-dir Task/BCH/simulation/stages/S2/stage07_multipath_validation/build -C Release --output-on-failure
Task/BCH/simulation/stages/S2/stage07_multipath_validation/build/stage07_multipath_validation_runner.exe Task/BCH/simulation/stages/S2/stage07_multipath_validation/results
matlab -batch "stage07_multipath_validation_matlab_reference(...)"
python Task/BCH/simulation/stages/S2/stage07_multipath_validation/python/stage07_multipath_validation_compare.py
python Task/BCH/simulation/stages/S2/stage07_multipath_validation/python/stage07_multipath_validation_check.py
git diff --check
git commit -m "BCH/stage07：实现多径模型与MMSE验证"
git push origin stage07-08-bch-s2-multipath
```

首次 C++ 构建暴露 stage01 `vector<unsigned>` 与 stage02 `BitVector` 类型边界，
显式转换后完整重跑。MATLAB 前两次分别因导入选项和数值转字符串精度损失失败；
修复后从 MATLAB、比较到 checker 全部重跑。
