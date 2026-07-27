# stage04_error_capability 规格冻结

每个独立 BCH 码块覆盖 `0..t+2`。`0..t` 为保证区，所有模式必须恢复原 payload；
`t+1/t+2` 不预设必须失败，只按真实行为分类为 TRUE_SUCCESS、DETECTED_FAILURE、
MISCORRECTION、UNDETECTED_ERROR 或 INVALID_CONFIGURATION。

错误模式覆盖系统区、校验区、首尾、连续位置、系统/校验边界和确定性随机位置。
BCH(15,11,1) 额外覆盖全部 15 个单错位置、同块双错、跨块双错及每块一个错误。

Gate：`PASS_STAGE04_ERROR_CAPABILITY`
