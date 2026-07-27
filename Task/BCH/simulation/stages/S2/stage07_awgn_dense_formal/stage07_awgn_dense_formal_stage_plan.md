# Stage07 BCH S2 AWGN Dense Formal Plan

## Goal

Create a new high-density BCH S2 AWGN formal experiment under
`Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal`.

This stage does not modify or overwrite `stage06_awgn_formal`. Stage06 remains the low-density
baseline and historical evidence.

## Non-goals

- Do not redefine Stage02 case contracts.
- Do not modify BCH encoder, decoder, payload reassembly, random identity, or AWGN model.
- Do not interpolate, smooth, fit, or replace measured points.
- Do not modify `Task/CC` or `Task/LDPC`.
- Do not merge `main`, rebase, amend, force push, reset, or delete old results.

## Frozen Experiment Contract

- Stage ID: `stage07_awgn_dense_formal`
- Master seed: `2026072707`
- Cases: the 8 frozen Stage02 BCH S2 cases
- X-axis physical quantity: waveform SNR
- SNR grid: `0.0:0.5:18.0` dB, inclusive
- Points per case: 37
- Total formal points: 296
- Stop rule per point: `minFrames=1000`, `targetFrameErrors=200`, `maxFrames=50000`
- Checkpoint interval: 1000 frames
- BPSK mapping: bit 0 -> +1, bit 1 -> -1
- SNR/EbN0 conversion: `EbN0_dB = SNR_dB - 10*log10(2*R)`
- Noise variance: `sigma2 = 1/10^(SNR_dB/10)`

## Outputs

- Formal raw results: `results/stage07_awgn_dense_formal_results.csv`
- Published results: `published_results/`
- Per-point raw artifacts: `results/points/<caseId>/snr_<index>/`
- Progress file: `results/stage07_awgn_dense_formal_progress.csv`
- Plots and figure-data: `plots/`
- Stage06 overlap comparison: `results/stage07_awgn_dense_formal_stage06_overlap_compare.csv`

## Gates

- `PASS_STAGE07_RESUME_EQUIVALENCE`
- `PASS_STAGE07_AWGN_DENSE_FORMAL_RUNNER`
- `PASS_STAGE07_AWGN_DENSE_FORMAL_PLOT`
- `PASS_STAGE07_AWGN_DENSE_PLOT_CHECK`
- `PASS_STAGE07_AWGN_DENSE_FORMAL`
- `PASS_BCH_S2_AWGN_DENSE_RERUN`
