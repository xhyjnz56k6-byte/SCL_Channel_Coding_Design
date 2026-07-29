# Stage09 两层 SNR 网格修订报告

本轮保留旧正式结果，不删除 825696 帧历史数据；新增 two_level 前缀结果作为修订视图。coarse 层由 runtime/two_level_coarse 真实补跑，覆盖 -5 到 10 dB、0.5 dB、6 个 case 共 186 点；dense 层采用旧已验证 waterfall formal 结果，合并表遇到重复 SNR 点时优先使用 dense_verified_legacy。全部 BER/FER 行均新增 95% Wilson 置信区间。
