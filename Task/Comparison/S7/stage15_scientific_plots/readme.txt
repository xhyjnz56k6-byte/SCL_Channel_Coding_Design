阶段名称：stage15_scientific_plots
实验目的：基于 Formal 和全起点原始 CSV 生成可审计科研图。
主要输入：Stage10～14 原始和派生 CSV。
完成内容：BCH 29 张、CC 21 张图全部生成；每图独立目录、6 类资产和 SHA 通过 checker；指定 BCH 样式图和 2%热力图已人工抽查渲染。
主要输出：42 个正式图目录、plot_inventory.csv、stage15_validation.json。
当前结论：正式图 Gate PASS；BCH 10%无区分度热力图已归档，当前正式展示 2%和5%；无零值伪替换、平滑、水平延伸、error floor 或上界标记。
已知问题：目标 FER 无法插值的图不显示伪造数值；首轮失败资产已归档且禁止使用。
阶段状态：PASS
