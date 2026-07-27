# Stage13 Commands Used

```powershell
cmake -S <stage13>/cpp -B <debug-build> -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Debug
cmake --build <debug-build> -j 2
ctest --test-dir <debug-build> --output-on-failure -V
cmake -S <stage13>/cpp -B <release-build> -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build <release-build> -j 2
stage13_burst_interleaving_validation_runner.exe <results> <masterSeed> <interleaverSeed>
matlab -batch "stage13_burst_interleaving_validation_matlab_reference(...)"
python stage13_burst_interleaving_validation_check.py
```
