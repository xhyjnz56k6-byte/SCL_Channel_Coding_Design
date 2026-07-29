# Stage11 验证报告

Gate：`PASS_STAGE11_CC_SOFT_QUANTIZATION`

分支 `stage01-cc`；base `16063360f65a9f6dd95887659f92e01561e5e948`；content `f4cad80c878c24653e01b3aa4b0100198ef783fb`；`mergeStatus=NOT_MERGED`。

已实际执行 Release 编译、四场景联合 clipping prescan、4000 帧正式矩阵、逐行公式/有限值/整数安全检查、Stage10 审计回归和 `git diff --check`。全局选择 clipMax=2；Q6 的最坏 BER/FER 增幅为 9.804%/6.780%，overflow 和 path metric saturation 均为 0，推荐 Q6。Q3/Q4 未通过性能门限。远程分支 `origin/stage01-cc` 已验证包含本 Stage 功能提交；未合并 `main`。
