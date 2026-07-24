# BCH16W9 commands used

Working directory:

```text
C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design
```

## Configure and build

The first default-generator configure attempt failed because `nmake` was unavailable:

```powershell
cmake -S Task\BCH\simulation\current `
  -B Task\BCH\simulation\build\bch16w9_decode_timing_snr_figures `
  -DCMAKE_BUILD_TYPE=Release
```

The successful Release build used the already validated MinGW toolchain:

```powershell
cmake -G "MinGW Makefiles" `
  -S Task\BCH\simulation\current `
  -B Task\BCH\simulation\build\bch16w9_decode_timing_snr_figures_mingw `
  -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_CXX_COMPILER=D:\Apps\MinGW\ucrt64\bin\c++.exe `
  -DCMAKE_MAKE_PROGRAM=D:\Apps\MinGW\ucrt64\bin\mingw32-make.exe

cmake --build `
  Task\BCH\simulation\build\bch16w9_decode_timing_snr_figures_mingw `
  --parallel
```

## Tests

```powershell
ctest --test-dir `
  Task\BCH\simulation\build\bch16w9_decode_timing_snr_figures_mingw `
  --output-on-failure

Task\BCH\simulation\build\bch16w9_decode_timing_snr_figures_mingw\test_bch11_noiseless.exe `
  Task\BCH\simulation\results\frame_pools\formal_k200\k200\manifest.json `
  Task\BCH\simulation\results\frame_pools\formal_k300\k300\manifest.json `
  Task\BCH\simulation\results\bch16w9_decode_timing_snr_figures\noiseless
```

## Timing experiment

`run_20260724_01` was interrupted by the outer command timeout and retained as an
incomplete result directory. It was not used.

The complete published run was:

```powershell
python Task\BCH\simulation\scripts\run_bch16w9_timing.py `
  --runner Task\BCH\simulation\build\bch16w9_decode_timing_snr_figures_mingw\bch_awgn_runner.exe `
  --formal-summary Task\BCH\simulation\stages\bch16w8_five_case_comparison\five_case_formal_summary.csv `
  --k200-manifest Task\BCH\simulation\results\frame_pools\formal_k200\k200\manifest.json `
  --k300-manifest Task\BCH\simulation\results\frame_pools\formal_k300\k300\manifest.json `
  --output-dir Task\BCH\simulation\results\bch16w9_decode_timing_snr_figures\run_20260724_02 `
  --warmup-frames 500 `
  --timed-frames 5000 `
  --repetitions 3
```

## Figures and functional Gate

```powershell
python Task\BCH\simulation\scripts\plot_bch16w9_snr_chinese.py `
  --formal-summary Task\BCH\simulation\stages\bch16w8_five_case_comparison\five_case_formal_summary.csv `
  --timing-summary Task\BCH\simulation\results\bch16w9_decode_timing_snr_figures\run_20260724_02\timing_summary.csv `
  --stage-dir Task\BCH\simulation\stages\bch16w9_decode_timing_snr_figures

python Task\BCH\simulation\scripts\check_bch16w9.py `
  --repo-root . `
  --formal-summary Task\BCH\simulation\stages\bch16w8_five_case_comparison\five_case_formal_summary.csv `
  --timing-result-dir Task\BCH\simulation\results\bch16w9_decode_timing_snr_figures\run_20260724_02 `
  --stage-dir Task\BCH\simulation\stages\bch16w9_decode_timing_snr_figures
```
