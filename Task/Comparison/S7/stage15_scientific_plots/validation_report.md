# Stage15 验证报告

- 正式图：50 张；BCH 29、CC 21。
- 每图 figure.png、figure_data.csv、plot_manifest.json、plot_validation.json、sha256.txt、readme.txt：42/42 完整。
- 原始数据绝对路径：全部存在。
- 历史 LDPC 路径：全部记录且 `historicalReferenceUsedInFigure=false`。
- SHA：全部一致。
- 平滑/伪小值/水平延伸/error floor/零错上界：0。
- nonMonotonicHighSnrAnomaly：0；BLOCKED 图：0。
- 中文标题、坐标轴和图例：抽查通过。
- v01 失败图资产：已归档，禁止用于正式结论。
- v02：旧 BCH 10%热力图和本轮覆盖前的十个 BCH 图资产已归档；正式 BCH 热力图改为 2%/5%，指定八幅 FER 图和相应 BER 图使用固定配置级样式。

Gate：PASS_STAGE15_SCIENTIFIC_PLOTS。
