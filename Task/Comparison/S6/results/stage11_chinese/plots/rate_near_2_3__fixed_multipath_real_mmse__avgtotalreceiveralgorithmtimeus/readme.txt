本目录保存一张从 S5 Formal 原始 CSV 逐点重绘的 Stage11 中文科研图。
figure.png 为重绘图；figure_data.csv 保留原始值和实际绘图值；plot_manifest.json 记录源文件、哈希、坐标、样式和零值策略。
BER/FER 原始零值保留在 CSV 中，但不在对数纵轴绘制；未使用平滑、插值或人工下限线。
所有生成文件禁止人工修改，应通过重绘脚本复现。
