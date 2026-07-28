# stage08_multipath_formal 文件说明

- `cpp/`：正式 runner，读取冻结 grid；按 Case/点生成独立 payload/AWGN，
  实现 5000/200/50000 停止规则、2 shard、每 1000 帧 checkpoint 与恢复。
- `python/stage08_multipath_formal_process.py`：合并 shard、生成整数计数汇总、
  runtime、checkpoint/shard manifest 和结论矩阵。
- `python/stage08_multipath_formal_check.py`：复算 rate、sigma2、SNR、BER、FER、
  停止规则、会计恒等式、有限值和 residual。
- `python/stage08_multipath_formal_plot.py`：只用 matplotlib 生成 8 个 PNG，
  同步生成 figure-data 与逐图 manifest。
- `python/stage08_multipath_formal_plot_check.py`：检查 PNG 头、尺寸、hash、
  figure-data、零值替代、图例、样式和禁止格式。
- `results/`：本次最终 formal 的两个 shard 和 24 点合并原始 CSV。
- `plots/`：8 个 PNG，每图独立 figure-data、manifest、checker log。
- 根目录 CSV/JSON/MD/log：正式汇总、runtime、merge/checkpoint/shard 审计、
  200/300 bit 结论和 Gate 证据。

复用 stage07 冻结信道与 MMSE core、stage01 随机/AWGN 数学、stage02 8 Case
契约以及既有 BCH 编解码核心；没有修改它们。首轮仅支持完成点 checkpoint 的
运行被拒绝作为最终 Gate，原样保存在本地忽略目录 `initial_e055724/`；
最终结果全部由修复提交 `5fb6a37...` 重新运行。
