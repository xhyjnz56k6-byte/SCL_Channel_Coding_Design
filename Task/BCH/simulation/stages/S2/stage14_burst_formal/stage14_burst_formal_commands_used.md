# Stage14 Commands Used

```powershell
python stage14_burst_formal_run.py
git commit -m "BCH/Stage14：实现无交织突发正式实验"
python stage14_burst_formal_run.py --formal
python stage14_burst_formal_check.py
```

正式运行使用 4 个点级 shard；每个点仍按 frameIndex 0 开始并独立停止。
