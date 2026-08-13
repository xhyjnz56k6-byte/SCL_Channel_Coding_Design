阶段名称：stage15_scientific_plots
实验目的：基于 Formal 和全起点原始 CSV 生成可审计科研图。
主要输入：Stage10～14 原始和派生 CSV。
完成内容：BCH 29张、CC 22张图全部生成；CC 5张适用BER/FER图加入LDPC无交织近码率AWGN基线，并新增1张CC/LDPC无突发纯译码CPU时间参考图；每图独立目录、资产和SHA通过checker。
主要输出：51个正式图目录、plot_inventory.csv、stage15_validation.json、ldpc_baseline来源审计与编码基线表。
当前结论：正式图 Gate PASS；无突发、突发无交织和突发有交织三个层级可直接区分；BCH 10%无区分度热力图已归档，当前正式展示 2%和5%。
已知问题：CC与LDPC没有统一operation-count口径；LDPC没有突发结果，只能作为AWGN参考；BCH历史Es/N0只画原始点、不插值；目标FER无法插值的图不显示伪造数值。
阶段状态：PASS
