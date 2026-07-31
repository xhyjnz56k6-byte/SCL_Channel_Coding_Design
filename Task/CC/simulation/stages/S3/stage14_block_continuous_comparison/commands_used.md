# Stage14 final-delivery commands

- Minimal Git audit: `git rev-parse --show-toplevel`, branch, HEAD and status.
- Release build: `cmake -S . -B build/final_delivery -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release`
- Build: `cmake --build build/final_delivery --parallel`
- Hard formal runner: `--decision hard --grid coarse --min-frames 1000 --target-frame-errors 200 --max-frames 50000`
- Formal execution: 93 idempotent SNR units, initially 8 shards; completed units were reused and remaining high-SNR units were assigned independent shard indices.
- Merge/plots: `python scripts/process_final_delivery.py`
- Checker: `python scripts/check_stage14.py`
- Reproducible entry: `python scripts/run_stage14.py`

No Stage14 Soft, Stage09, Stage10, Stage11 or Stage13 formal simulation was rerun.
