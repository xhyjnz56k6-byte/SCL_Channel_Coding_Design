# S5 Stage12与Stage11中文重绘执行报告

## 1. 本轮任务摘要

本轮严格串行完成Stage12已知连续擦除卷积码独立验证；Stage12 PASS后，归档原Stage11英文图，使用同一Stage10 Formal CSV重绘86张中文科研图、更新推荐逻辑并新增20张Aggregate图。未重跑Stage10 Formal。

## 2. 开始前Git状态

- 仓库：`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design`
- 分支：`S5-Compare`
- HEAD与`origin/S5-Compare`：`70572ad999f17339fb4a4a3d4b0fbfbda6dd168f`
- 开始时仅有已批准的Stage12规格冻结文件未跟踪；没有来源不明修改。

## 3. Stage12目的与删减边界

验证CC R2/3在5%已知连续擦除下FER接近1是否为真实敏感性，而非索引、打孔、LLR、Viterbi或统计错误。只做20个R2/3扫描点、3个R1/2补充点、8个MATLAB点和6个交织诊断点；未运行六信道Formal、全Grid、N560或新信道扫描。

## 4. 参数审计

payload 300 bit；K=7；171/133八进制；6个零尾比特；R1/2长度612；R2/3以`1101`相位0打孔为459；BPSK 0→+1、1→-1；`sigmaSquared=1/(2*10^(Es/N0/10))`；已知擦除发送位置LLR=0；完整306步终止Viterbi。17×27交织覆盖全部459符号，无填充、截断或部分交织。

## 5. 固定trace结果

R2/3选择frame 0和1，5%擦除起点分别92、282，间距190，大于23符号擦除长度。无噪声无擦除链路零错误。5%擦除trace的payload错误为局部少量错误：frame 0为5 bit、错误跨度8；frame 1为8 bit、错误跨度9。FER接近1不表示每帧全部bit随机错误，而是几乎每帧至少出现一个局部payload错误。

## 6. C++擦除比例扫描

完成R2/3的0/1/2/3/5% × 0/4/8/10 dB共20点。高SNR的5%结果：4 dB为998/1000、FER=0.998；8 dB为998/1000、FER=0.998；10 dB为998/1000、FER=0.998。R1/2补充3点均为999/1000、FER=0.999。BER和FER均可由整数计数复算，无NaN/Inf。

## 7. MATLAB官方独立验证

MATLAB R2024b使用`poly2trellis(7,[171 133])`、`convenc`、`vitdec`独立生成payload、编码、打孔、噪声、LLR和译码。固定向量只共享原始payload，母码、459个发送bit和无噪声payload与C++逐bit一致。独立统计的5%结果：4/8/10 dB FER分别为0.999、0.999、1.000。

## 8. C++与MATLAB一致性

两种实现均独立复现高SNR严重FER平台；95% Wilson区间重叠。MATLAB满足`FER≥0.99` Gate。未发现使Stage10结果失效的实现错误。

## 9. 交织诊断

17×27交织/逆交织无噪声逐bit恢复正确。5%连续擦除下，4/8/10 dB各运行5000帧，交织诊断均为0帧错误；无交织均为998/1000帧错误。该结果仅说明连续损伤被时间分散后机制显著变化，标记为`diagnostic_only`，不进入S5推荐或替代S7。

## 10. Stage10有效性

Stage10的5%已知连续擦除结果继续有效。Formal CSV未修改、未移动、未重跑，SHA-256始终为`dbeb75842f8ecd5874e58153f908505884395750614ab75a6a33cdc3e3739947`。

## 11. Stage11归档与中文重绘

原86图及其sidecar、五张汇总表、Stage11审计记录和原脚本已归档至`results/stage11/archive/v01_20260803_before_chinese_replot_and_aggregate/`。使用Microsoft YaHei和同一Formal CSV重绘86张中文图，86/86通过审计；零错误点保留在CSV并在对数轴省略。

## 12. 推荐逻辑更新

推荐优先比较FER=0.1覆盖、FER=0.01覆盖、目标所需Es/N0、相对自身AWGN损失，再比较平均/P95/最大译码时延。双方均未覆盖FER=0.1时，只比较6–10 dB实测FER并明确未达到目标，禁止外推或跨零点插值。

## 13. Aggregate结果

新增20张中文多曲线图，每图独立目录包含PNG、原始绘图数据、manifest、检查报告、SHA和中文说明。所有曲线直接来自Stage10 Formal的31个真实SNR点；未混入Stage12数据；20/20通过审计。

## 14. 已知限制

- 固定trace数量有限；统计验证使用独立随机序列，不要求逐帧一致。
- 交织仅为最小机制诊断。
- 软件时延与当前主机相关；受控信道结论不外推为通用卫星信道结论。
- 当前功能修改尚未提交，functional range不能伪造为未来commit。

## 15. Git与未执行事项

- commit：`NOT_CREATED_NO_AUTHORIZATION`
- push：`NOT_RUN_NO_AUTHORIZATION`
- merge：`NOT_RUN_NO_AUTHORIZATION`
- 未进入S6或S7；未合并main。

## 16. 最终Gate

- `PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION`
- `PASS_S5_STAGE11_CHINESE_REPLOT`
- `PASS_S5_AGGREGATE_PLOT_AUDIT`
- `PASS_S5_STAGE11_STAGE12_FINAL_INTEGRATION`
- 最终：`PASS_S5_STAGE12_AND_REPLOT_COMPLETE`
