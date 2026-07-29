# Stage09 命令

```powershell
python Task/CC/simulation/stages/S3/stage09_awgn_formal/scripts/run_stage09.py --clean
cmake --build Task/CC/simulation/stages/S3/stage09_awgn_formal/build --parallel
stage09_awgn_formal_runner.exe runtime/formal_v2 --shard-index 0 --shard-count 2 --min-frames 5000 --target-frame-errors 200 --max-frames 50000 --checkpoint-interval 1000
stage09_awgn_formal_runner.exe runtime/formal_v2 --shard-index 1 --shard-count 2 --min-frames 5000 --target-frame-errors 200 --max-frames 50000 --checkpoint-interval 1000
python Task/CC/simulation/stages/S3/stage09_awgn_formal/scripts/merge_and_plot_stage09.py runtime/formal_v2 results
python Task/CC/simulation/stages/S3/stage09_awgn_formal/scripts/merge_and_plot_stage09.py --check-existing results
python Task/CC/shared/scripts/cc_stage_audit.py Task/CC/simulation/stages/S3/stage08_awgn_prescan/manifest.json
git diff --check
```

首次 `formal/` 运行暴露 R23/R34 的 0.2 dB 网格无法同时覆盖冻结端点，merge 以“工作单元不足”失败，未生成正式输出。修正为 0.1 dB 后使用新的 `formal_v2/` 运行，未覆盖失败资产。
