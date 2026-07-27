# Stage16 Commands Used

```powershell
python stage16_burst_interleaving_comparison_run.py
git commit -m "BCH/Stage16：实现AWGN突发适应性与综合比较"
python stage16_burst_interleaving_comparison_run.py --formal
python stage16_burst_interleaving_comparison_check.py
```

正式运行使用 4 个点级 shard，每点独立执行 1000/200/50000/1000 停止规则。
