# Stage07 BCH S2 AWGN Dense Formal Validation Report

## Scope

Stage07 adds a new dense waveform-SNR AWGN formal experiment at
`Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal`.

The Stage02 case contract is reused without redefining case fields. Stage06 is preserved as the
low-density baseline.

## Formal Experiment

- Stage ID: `stage07_awgn_dense_formal`
- Branch: `stage07-bch-s2-awgn-dense-formal`
- Baseline commit: `8bd58cf80c60f2d373d479b9d8e02a1919fdca8d`
- Functional commit: `f3c03718a69a41aeb72e9b7b6a2d9e017930bb19`
- Master seed: `2026072707`
- Cases: 8
- SNR grid: `0.0:0.5:18.0` dB
- Points per case: 37
- Total formal points: 296
- Frames per point: 1000 to 50000
- Total processed frames: 8824146
- Target-frame-error stops: 127
- Max-frame stops: 169
- Zero BER points: 147
- Zero FER points: 147
- Parallelism: one local runner process; independent per-point output directories

## Case Rates

| Case | Payload | Encoded length | Actual rate | Points |
|---|---:|---:|---:|---:|
| K200_S15 | 200 | 285 | 0.70175438596491224 | 37 |
| K200_M255K207 | 200 | 248 | 0.80645161290322576 | 37 |
| K200_M511K421 | 200 | 290 | 0.68965517241379315 | 37 |
| K200_M511K385 | 200 | 326 | 0.61349693251533743 | 37 |
| K300_S15 | 300 | 420 | 0.7142857142857143 | 37 |
| K300_M255K207 | 300 | 396 | 0.75757575757575757 | 37 |
| K300_M511K421 | 300 | 390 | 0.76923076923076927 | 37 |
| K300_M511K385 | 300 | 426 | 0.70422535211267601 | 37 |

## Executed Checks

| Check | Evidence | Result |
|---|---|---|
| CMake configure/build | `logs/stage07_awgn_dense_formal_ctest.log` | PASS |
| CLI negative validation through CTest | `logs/stage07_awgn_dense_formal_ctest.log` | PASS |
| Resume equivalence, 3000 frames vs 1000+2000 | `logs/stage07_awgn_dense_formal_resume_test.log` | PASS_STAGE07_RESUME_EQUIVALENCE |
| Formal runner, 296 points | `logs/stage07_awgn_dense_formal_runner.log` | PASS_STAGE07_AWGN_DENSE_FORMAL_RUNNER |
| Matplotlib PNG and figure-data generation | `logs/stage07_awgn_dense_formal_plot.log` | PASS_STAGE07_AWGN_DENSE_FORMAL_PLOT |
| Strict checker | `logs/stage07_awgn_dense_formal_check.log` | PASS_STAGE07_AWGN_DENSE_PLOT_CHECK |
| Stage audit script | `python/stage07_awgn_dense_formal_audit.py` | PASS_STAGE07_AWGN_DENSE_FORMAL_AUDIT |

## Checker Coverage

- 296 row result completeness.
- 8 cases with exactly 37 SNR points each.
- `snrIndex=0..36` and `snrDb=0.0..18.0` in 0.5 dB steps.
- `actualRate = payloadLength / encodedLength`.
- `snrLinear = 10^(snrDb/10)`.
- `EbN0_dB = SNR_dB - 10*log10(2*actualRate)`.
- `sigma2 = 1/snrLinear = 1/(2*actualRate*10^(EbN0_dB/10))`.
- Stop rule: min 1000 frames, target 200 payload-error frames, max 50000 frames.
- Raw BER/FER recomputation from integer counters.
- `trueSuccessFrames + payloadErrorFrames = totalFrames`.
- 296 checkpoint JSON files, 296 point result CSVs, 296 point logs.
- 6 PNG files only; no PDF/SVG/EPS/JPG/JPEG.
- 6 figure-data CSV files with 148 rows each and aggregate figure-data with 888 rows.
- Plot manifest and all referenced hashes verified.

## Stage06 Comparison

`results/stage07_awgn_dense_formal_stage06_overlap_compare.csv` records `NO_EXACT_OVERLAP`.
Stage06 used per-case Eb/N0 grids; Stage07 uses a unified waveform-SNR grid, so no exact waveform
SNR overlap was found by the strict checker. No Stage06 result was used to fill or alter Stage07.

## Gates

PASS_STAGE07_RESUME_EQUIVALENCE

PASS_STAGE07_AWGN_DENSE_FORMAL_RUNNER

PASS_STAGE07_AWGN_DENSE_FORMAL_PLOT

PASS_STAGE07_AWGN_DENSE_PLOT_CHECK

PASS_STAGE07_AWGN_DENSE_FORMAL

PASS_STAGE07_AWGN_DENSE_FORMAL_AUDIT

PASS_BCH_S2_AWGN_DENSE_RERUN

## Notes

Decoder latency is machine-dependent and represents this local Windows/MinGW environment. Raw CSV
BER and FER retain observed zero values; log-scale plots use only the documented display surrogate.
