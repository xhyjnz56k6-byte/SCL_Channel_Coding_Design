# Stage07 BCH S2 AWGN Dense Formal Known Issues

- No blocking issues.
- Runtime and decoder latency are machine-dependent for this Windows/MinGW run.
- Stage07 uses one local runner process. Outputs are still separated by formal point, so the result is auditable and resumable by point.
- `results/points/` contains full per-point checkpoints and logs for local audit continuity, but these large intermediate artifacts are not committed by default.
- BER/FER zero values remain zero in raw CSV. Zero-observed high-SNR points are censored in
  figure-data and `published_results/stage07_awgn_dense_formal_error_floor_analysis.csv`; log plots
  omit those censored points from the main curve, so the FER/BER figures no longer show a false
  measured nonzero floor.
- No exact waveform-SNR overlap with Stage06 was found because Stage06 used per-case Eb/N0 grids.
