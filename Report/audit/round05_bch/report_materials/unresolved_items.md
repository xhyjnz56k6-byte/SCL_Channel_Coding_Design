# 未解决项

1. Stage07 AWGN dense 与 Stage08 multipath common-SNR 的原图横轴是 `2Es/N0`，第4章使用前需生成不覆盖原文件的 Es/N0 图源和图；不需要重跑 formal。
2. Stage17 全信道 integration 的最终 Gate 因源分支空白字符检查被阻断；逐信道数值 checker 已通过，但暂不声称严格的全信道统一排名。
3. 旧 `batch2_corrected` 固定初始载波相位灵敏度结果缺少当前同级源码/manifest 追溯，只能作为附录或历史验证材料。
4. BCH16W9 的 `known_issues.md` 仍保留“Stage-C 未执行”的历史文字，尽管相关文件已有提交；正文引用时以当前 Git 提交和本轮冻结为准，不把该旧文字改写成新的算法 Gate。
5. S1 的 MATLAB 逐帧同噪声 formal 曲线对比曾记录为未完成；现有 MATLAB 证据覆盖 codec/代表性译码，不应扩写为完整曲线逐点一致。

以上均不要求修改 BCH/Common 算法，也不阻止参数和逐信道结果写作；第1项会阻止原 Stage07/08 PNG 直接作为 Es/N0 主图。
