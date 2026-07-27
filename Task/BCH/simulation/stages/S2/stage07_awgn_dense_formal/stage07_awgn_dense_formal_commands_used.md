# Stage07 BCH S2 AWGN Dense Formal Commands Used

```powershell
git switch -c stage07-bch-s2-awgn-dense-formal
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_run.py
cmake -S Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\cpp -B Task/BCH/simulation/build/S2/stage07_awgn_dense_formal -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build Task/BCH/simulation/build/S2/stage07_awgn_dense_formal --config Release -j 2
ctest --test-dir Task/BCH/simulation/build/S2/stage07_awgn_dense_formal -C Release --output-on-failure -V
Task/BCH/simulation/build/S2/stage07_awgn_dense_formal/stage07_awgn_dense_formal_runner.exe --resume-test <results> 2026072707 <configHash> <gitCommit>
Task/BCH/simulation/build/S2/stage07_awgn_dense_formal/stage07_awgn_dense_formal_runner.exe <pointsCsv> <results> 2026072707 <configHash> <gitCommit>
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_plot.py
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_check.py
git commit -m "BCH/stage07：完成高密度AWGN正式实验"
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_audit.py
```

The initial Python command was interrupted by the Codex tool timeout, but its child runner continued
and completed. The parent Python process then completed plot and checker generation.
