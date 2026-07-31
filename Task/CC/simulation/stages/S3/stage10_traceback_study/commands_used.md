# stage10_traceback_study commands used

- Release build: `cmake -DCMAKE_BUILD_TYPE=Release`
- Formal stopping: `--min-frames 1000 --target-frame-errors 200 --max-frames 50000`
- Coarse grid: `-5:0.5:10 dB`
- Dense grid: `0.1 dB` in the measured waterfall range
- Shards were merged only after every shard emitted its PASS sentinel and stderr remained empty.
- Plot processors generated pointwise figure-data CSVs, PNGs, plot manifests and SHA-256 checks.
