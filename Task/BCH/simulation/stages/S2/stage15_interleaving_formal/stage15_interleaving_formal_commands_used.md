# Stage15 Commands Used

```powershell
python stage15_interleaving_formal_run.py
git commit -m "BCH/Stage15：实现交织方式与深度正式实验"
python stage15_interleaving_formal_run.py --formal
python stage15_interleaving_formal_check.py
```

正式运行使用方式与深度各 4 个点级 shard；每个点独立执行冻结停止规则。
