# BCH S2-test archive index

This archive reorganizes the existing BCH S2 semi-finished experiment. It
does not rerun formal simulations, change source data, or select a final
coding scheme.

## Layout

- `current/S2-test/`: S2-specific C++ multipath/MMSE code and tests;
- `scripts/S2-test/`: S2 drivers, checks, comparisons, plots, and finalizers;
- `stages/S2-test/`: migrated S2 Stage audit records;
- `results/S2-test/`: local result archives, excluded from Git tracking;
- `matlab_official_validation/S2-test/`: S2 MATLAB reference entry points;
- `build/S2-test/`: generated S2 build output.

## Preserved distinctions

Shared AWGN simulation and case-adapter code remain in their original
locations. Original and corrected results remain separate, and the burst
original/redesign distinction is retained in the result archive.

## Stage index

The migrated tracked Stages are `s2_01_channel_contract`,
`s2_02_multi_channel_foundation`, `s2_03_awgn_baseline_reuse`,
`s2_04_fixed_multipath_mmse`, and `s2_batch1_fixed_multipath_mmse`.
Additional local-only S2 result collections are recorded in the ownership
and migration audits.

## Limitations

The S2 case matrix is incomplete, residual-CFO initial-phase behavior needs
further work, fixed multipath results depend on the frozen MMSE setup, and
the existing S2 data must not be treated as a final scheme-selection study.
