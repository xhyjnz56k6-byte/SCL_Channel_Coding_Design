# Stage07 BCH S2 AWGN Dense Formal Known Issues

- No blocking issues.
- Runtime and decoder latency are machine-dependent for this Windows/MinGW run.
- Stage07 uses one local runner process. Outputs are still separated by formal point, so the result is auditable and resumable by point.
- `results/points/` contains full per-point checkpoints and logs for local audit continuity, but these large intermediate artifacts are not committed by default.
- BER/FER zero values remain zero in raw CSV. Plot-only surrogates are documented in figure-data and the plot manifest.
- No exact waveform-SNR overlap with Stage06 was found because Stage06 used per-case Eb/N0 grids.
