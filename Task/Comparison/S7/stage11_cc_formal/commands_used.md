# Stage11 命令

```powershell
Task\Comparison\S7\build\stage10_formal\s7_formal_runner.exe CC Task\Comparison\S7\stage11_cc_formal\results
python Task\Comparison\S7\scripts\check_formal.py CC Task\Comparison\S7\stage11_cc_formal\results
```

runner 正常完成 558/558 组；checker 输出 `PASS_S7_CC_FORMAL rows=2232 groups=558`。
