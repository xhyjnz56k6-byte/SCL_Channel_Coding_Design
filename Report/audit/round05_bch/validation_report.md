# Round05-A validation report

## 实际执行

- Git 根目录、分支、status、HEAD、worktree、remote：PASS。
- 五方案参数与分组/整块 profile 交叉核验：PASS。
- S1 五方案主 CSV 74 行逐行计数/BER/FER/状态/码率复算：PASS。
- S1 W9 六个图源 222 行 Es/N0 公式复算：PASS。
- S2 五条正式主数据共 1816 行计数/BER/FER/状态/码率复算：PASS。
- Stage10/12/16 Es/N0 公式：PASS。
- Stage07/08 轴口径：检测到稳定 +3.0102999566 dB 差异，已定位为 waveform-SNR=`2Es/N0`，`AXIS_CONVERSION_REQUIRED`。
- 原始零错误点保留、未生成 error floor：PASS。
- 新目录 readme 存在、非空、含中文并说明目的/作用/内容：PASS。
- 范围检查：仅新增 `Report/audit/round05_bch`，未修改其他模块：PASS。

## Gate

- Gate A 仓库安全：PASS
- Gate B 目录规范：PASS
- Gate C 方案冻结：PASS
- Gate D 源码冻结：PASS
- Gate E S1结果冻结：PASS
- Gate F S2结果冻结：PASS_WITH_INTEGRATION_LIMITATION
- Gate G 数据质量：PASS_WITH_AXIS_CONVERSION_REQUIRED
- Gate H 写作素材：PASS
- Gate I 范围控制：PASS

本轮未执行 build、CTest、MATLAB 或 formal；不得把这些测试标记为本轮 PASS。既有 Stage Gate 只作为版本裁定证据。
