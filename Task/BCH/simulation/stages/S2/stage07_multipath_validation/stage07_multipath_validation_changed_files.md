# stage07_multipath_validation 文件与复用说明

- `cpp/stage07_multipath_validation_core.*`：基于旧
  `fixed_multipath_mmse.cpp` 的固定 FIR、完整卷积和带状 Cholesky 思路重构；
  新增 stage02 Case 适配、完整残差、NaN/Inf 和尺寸检查。
- `cpp/stage07_multipath_validation_runner.cpp`：新建 8 Case 验证 runner，替代旧
  五 Case 硬编码 runner。
- `matlab/stage07_multipath_validation_matlab_reference.m`：由旧 MATLAB 参考的
  独立 `H` 构造与反斜杠求解思路适配，不读取 C++ 输出作为计算输入。
- `python/`：新建连续量/离散量比较和业务 Gate checker。
- `results/` 与 `logs/`：本次运行产生的小型验证证据，不复制历史 CSV/PNG。
- `stage08_multipath_formal_config.json` 与 frozen grid：作为 stage07 Gate
  前置条件人工冻结；没有执行 stage08 formal。

直接复用且未修改：stage01 随机/AWGN 数学基础、stage02 Case Contract、block
和 segmented BCH 编解码源码。

拒绝复用：旧五 Case runner、旧自动 grid、旧 formal CSV/PNG 和旧随机键。
没有从零重写正确的 BCH 编解码算法。
