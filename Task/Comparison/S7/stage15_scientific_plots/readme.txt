阶段名称：stage15_scientific_plots
实验目的：基于 Formal 和全起点原始 CSV 生成可审计科研图。
主要输入：Stage10～14 原始和派生 CSV。
完成内容：BCH 29 张、CC 21 张图全部生成；14 张适用 BER/FER 与纯译码时间图加入严格匹配的历史无突发 AWGN 基线；每图独立目录、资产和 SHA 通过 checker。
主要输出：42 个正式图目录、plot_inventory.csv、stage15_validation.json。
当前结论：正式图 Gate PASS；无突发、突发无交织和突发有交织三个层级可直接区分；BCH 10%无区分度热力图已归档，当前正式展示 2%和5%。
已知问题：历史复杂度操作计数不存在，明确记为 N/A；BCH 历史 Es/N0 网格与 S7 相差固定 10log10(2) 口径换算，仅画原始点，不插值；目标 FER 无法插值的图不显示伪造数值。
阶段状态：PASS
