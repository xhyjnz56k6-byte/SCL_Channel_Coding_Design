# BCH S2 AWGN 实验结果

本目录集中保存 BCH S2 AWGN stage01 至 stage06 的可审查输出，按 Stage 分类，避免与历史 `smoke`、`prescan`、`formal` 和 `comparison` 结果混淆。

## 目录分类

- `stage01_foundation/results/`：AWGN 基础向量、C++/MATLAB 对照和随机性测试输出。
- `stage02_case_contract/results/`：8 个正式 Case 的配置、码长、码率、组帧和映射审计输出。
- `stage03_noiseless/results/`：无噪声编码译码摘要、逐帧结果和 C++/MATLAB 对照输出。
- `stage04_error_capability/results/`：误差注入、纠错能力和误纠状态输出。
- `stage05_awgn_trial/results/`：试运行结果、点配置、续跑/分片合并审计和停止规则测试；`plots/` 保存试运行曲线及其 figure-data。
- `stage06_awgn_formal/results/`：正式 AWGN 结果、点级结果、分片清单和合并审计；`plots/` 保存正式 BER/FER/时延曲线及其 figure-data。

checkpoint、build 产物和大型帧池继续保留在各 Stage 的本地工作目录，不复制到本汇总目录。

## 可追溯性

- 实验线路：`stage01-06-bch-s2-awgn`
- 当前审计 HEAD：`8bd58cf80c60f2d373d479b9d8e02a1919fdca8d`
- 最终 Gate：`PASS_BCH_S2_AWGN_STAGE01_TO_STAGE06`
