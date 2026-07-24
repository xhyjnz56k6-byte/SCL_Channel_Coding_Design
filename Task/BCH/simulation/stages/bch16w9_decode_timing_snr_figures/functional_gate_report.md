# BCH16W9 functional Gate report

## Outcome

```text
PASS_BCH16W9_FUNCTIONAL_GATE
profileCaches=3
timingPoints=74
timingMeasurements=222
figures=6
```

## Root-cause repair

- BCH-B200, BCH-B300 and BCH-B300-426 now each own one function-local static
  `BlockBchProfile`.
- `blockProfile` returns `const BlockBchProfile&`; the per-frame encode/decode paths
  no longer construct a profile or generator polynomial.
- `prepareBchCase` initializes the selected whole-block profile or segmented
  syndrome table before the AWGN per-frame timing loop.
- The optional timing warmup executes complete frames without adding them to
  correctness counters or latency statistics.

## Tests actually executed

- Release configure/build with MinGW GCC 15.2.0: PASS.
- CTest: 6/6 PASS.
  - BCH(15,11) encoder
  - syndrome table
  - lookup decoder
  - segmented adapter
  - whole-block BCH
  - AWGN/rate/noise/repeated-use regression
- Five-case common-pool noiseless integration: PASS.
- Invalid case and invalid payload-length rejection remain covered by the
  noiseless integration test.

## Timing experiment

- Cases: BCH-S200, BCH-B200, BCH-S300, BCH-B300, BCH-B300-426.
- Formal points: 74.
- Warmup: 500 frames per point and repetition.
- Timed frames: 5000 per point and repetition.
- Repetitions: 3.
- Published statistic: median of the three per-repetition means.
- Complete measurements: 222.
- All latency values are finite and strictly positive.

Frame-weighted old versus repaired average decode times:

| Case | Old (μs) | Repaired (μs) | New/old |
|---|---:|---:|---:|
| BCH-S200 | 14.832 | 13.236 | 0.892 |
| BCH-B200 | 47.711 | 26.982 | 0.566 |
| BCH-S300 | 21.967 | 20.362 | 0.927 |
| BCH-B300 | 127.740 | 73.178 | 0.573 |
| BCH-B300-426 | 1978.779 | 103.732 | 0.052 |

The repaired B300-426 result is no longer dominated by per-frame t=14 generator
construction. Its remaining cost is higher than B300, consistent with the larger
syndrome/Berlekamp-Massey/Chien workload.

## SNR conversion and figures

- Every point uses
  `snrDb = sourceEbN0Db + 10*log10(payloadLength/encodedLength)`.
- Formula audit tolerance: `1e-12 dB`.
- BER and FER values are bit-for-bit numerically unchanged after conversion.
- Six PNG files and six figure-data CSV files were generated.
- Titles, axes and legends match the Stage-A frozen Chinese text.
- Manual visual inspection passed for Chinese glyph rendering, curve distinction,
  legend readability and axis units.

## Functional-stage limitations

- BER/FER simulation was not rerun because only the exactly derived horizontal
  coordinate changed; the validated W8 BER/FER values were preserved.
- Timing is Windows software latency on this machine, not a hardware decoder
  latency claim. Three-repeat medians reduce but do not eliminate OS scheduling
  variation.
- No new MATLAB run was performed: the BCH mathematical outputs and parameters
  were not changed, and existing official/reference validation remains the source
  for algorithm correctness.
- Functional changes are not committed or pushed in Stage B.
