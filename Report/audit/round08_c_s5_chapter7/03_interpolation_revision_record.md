# FER门限插值口径修订记录

Round08-A首版 `12_s5_result_evidence_matrix.csv` 曾采用FER线性域插值，和权威 `stage11_analysis.py` 的规则不一致。已将 Round08-A 扫描脚本统一为：在相邻真实、非零 FER 测点之间对 `log10(FER)` 作线性插值。

第7章表7.4、表7.5、正文门限与损失数字，以及表7.8中的推荐均使用该修订后的对数域插值结果。任一目标没有被相邻非零测点覆盖时保持 N/A，不进行范围外外推。

Formal原始CSV、744个正式scheme points、BER/FER数据、图像像素和信道算法均未修改，也未重新运行Formal。
