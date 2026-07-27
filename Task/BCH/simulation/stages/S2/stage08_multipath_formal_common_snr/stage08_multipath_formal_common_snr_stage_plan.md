# stage08_multipath_formal_common_snr

目标：在统一接收波形 SNR 横坐标下完成 BCH S2 固定多径正式补充实验。

非目标：不修改 Stage07 多径模型，不覆盖旧 Stage08 宽网格结果，不修改 CC/LDPC/Common。

范围：仅新增 Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr。

Gate：self-test、checkpoint/resume、shard/merge、results checker、plot checker、audit 全部 PASS 后提交并 push。
