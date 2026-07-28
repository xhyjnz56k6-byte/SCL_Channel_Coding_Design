# stage04_error_capability 验证报告

最终 Gate：`PASS_STAGE04_ERROR_CAPABILITY`

- Release 构建和 CTest 1/1：PASS。
- `0..t` 保证区：767 个模式全部 TRUE_SUCCESS。
- `t+1/t+2` 及额外边界模式：650 个真实分类。
- 超能力区分类：TRUE_SUCCESS 28、DETECTED_FAILURE 70、MISCORRECTION 552、
  UNDETECTED_ERROR 0、INVALID_CONFIGURATION 0。
- BCH(15,11,1) 全部单错位置：30/30 PASS。
- 同块双错按真实结果分类；跨块每块单错和所有分块各单错正确恢复。
- K300_M255K207 两个缩短块各单错正确恢复。
- MATLAB R2024b 关键 `0 error/t errors` 样本：16/16 mismatch=0。

没有要求超能力区全部显式失败，也没有把误纠计为成功。所有结果均保存原始分类。

- functional base：`acbebade03a99e1f2dfc5ff201dba3646381d130`
- functional content：`6e8841446a885f1c1a6a9fdb7214f2ed573fd9dd`
- 修改范围仅为 stage04。
- 本地生成 `results/` 未进入 functional commit。
- push 未获当前 AWGN 分支授权；`main` 未合并。
