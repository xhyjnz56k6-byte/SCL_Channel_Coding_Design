# stage03_noiseless 实际命令

```powershell
python Task/BCH/simulation/stages/S2/stage03_noiseless/python/stage03_noiseless_run.py
python Task/BCH/simulation/stages/S2/stage03_noiseless/python/stage03_noiseless_check.py
```

运行器执行 Release CMake/MinGW 构建、CTest（8056 帧完整链路）、MATLAB R2024b
8 Case 样本编码/恢复参考和 Python 业务 checker。

首次执行在编译阶段发现 stage01 `vector<unsigned>` 与 BCH `vector<uint8_t>` 的接口
类型不一致。stage03 增加显式二进制转换后，第二次完整重跑通过。首次失败没有执行
stage03 测试，也没有进入 stage04。
