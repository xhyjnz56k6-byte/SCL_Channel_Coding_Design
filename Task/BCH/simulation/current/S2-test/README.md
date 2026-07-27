# BCH S2-test C++

This directory contains the BCH S2-specific multipath/MMSE implementation,
runner, MATLAB vector exporter, and unit test. Shared AWGN and case-adapter
code remains in the parent `current` directory.

Build from the repository root:

```text
cmake --fresh -G "MinGW Makefiles" -S Task/BCH/simulation/current -B Task/BCH/simulation/build/S2-test -DCMAKE_BUILD_TYPE=Release
cmake --build Task/BCH/simulation/build/S2-test --config Release -j 4
ctest --test-dir Task/BCH/simulation/build/S2-test --output-on-failure
```
