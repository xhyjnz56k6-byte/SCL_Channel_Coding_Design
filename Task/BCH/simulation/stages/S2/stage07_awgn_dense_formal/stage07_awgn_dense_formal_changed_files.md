# Stage07 BCH S2 AWGN Dense Formal Changed Files

Stage07 adds a new experiment directory only:

- `configs/`: frozen dense waveform-SNR configuration.
- `cpp/`: dense formal C++ runner and CMake target.
- `python/`: run, plot, check, and audit scripts.
- `plots/`: six PNG figures, six per-figure CSV files, aggregate figure-data, and plot manifest.
- `published_results/`: small published CSV/JSON result artifacts.
- `results/`: committed small summary/progress/raw-result audit files; full `results/points/` remains local.
- `logs/`: executed build/test/runner/plot/check logs.
- root stage files: plan, acceptance matrix, frozen config/grid, validation report, known issues, manifest, commands, hashes, patch, and commit record.
- Error-floor repair: plot/check scripts now mark zero-observed BER/FER points as censored and
  publish `published_results/stage07_awgn_dense_formal_error_floor_analysis.csv`.
- False-floor plot repair: BER/FER log plots omit censored zero-observed points from the main curve,
  so the high-SNR FER figures stop at the last measured nonzero point instead of showing a false
  horizontal error floor.

No `Task/CC`, `Task/LDPC`, `main`, or Stage06 files are modified.
