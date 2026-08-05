# S7 BCH 图样式、热力图与 BER 图修订报告

## 修改原因

原 BCH 10% 全起点热力图中全部配置、全部起点的 FER 均为 1，缺乏区分度；同时为对应 BCH FER 展示补充 BER 曲线，并提高接近/重合 BCH 曲线的可辨识性。

## 修改前后图清单

- 修改前：BCH 21 张、CC 21 张，共 42 张；BCH 正式全起点图为 10%。
- 修改后：BCH 29 张、CC 21 张，共 50 张；BCH 正式全起点图为 2% 和 5%。
- 新增 BER 图：`22_burst_5_ber`、`23_burst_10_ber`、`24_mean_position_ber`、`25_max_position_ber`、`26_min_position_ber`、`27_absoluteBerImprovement`、`28_relativeBerReductionPercent`；既有 `02_methods_ber` 同步采用固定样式。

## 修改的 BCH FER 图

`01_methods_fer`、`04_burst_5_fer`、`05_burst_10_fer`、`07_mean_position_fer`、`08_max_position_fer`、`09_min_position_fer`、`11_absoluteFerImprovement`、`12_relativeFerReductionPercent`。

固定样式为：无交织实线实心圆；BCH码块交织 D=19 虚线空心圆；行列交织 rows=15 点划线实心方块；全帧伪随机交织点线空心三角。线型和标记只提高可辨识性，不改变 figure-data、统计方法或结论。

## BCH 全起点热力图

- 2%：原始路径 `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage12_all_start_scan\results\bch_2_percent\all_start_results.csv`；补扫 3360 行/840 组，HIGH 工作点含 280 个完整合法起点。
- 5%：原始路径 `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage12_all_start_scan\results\bch\all_start_results.csv`；HIGH 工作点含 272 个完整合法起点。
- 10%：旧图已归档到 `stage15_scientific_plots/archive/v02_20260805_before_bch_plot_style_and_heatmap_update/bch/21_all_start_heatmap_moved_from_current/`；原始 10% 数据未删除。因所有起点和配置 FER=1，不再列入当前正式图清单。

两张当前热力图均使用原始 FER、nearest、完整起点、固定色条范围 0～1；未插值、平滑或删除异常点。

## 验证与未修改范围

- Stage12 BCH 2% 补扫：PASS；configHash 单一，NaN/Inf=0，共享 payload/noise/frame hash 完整。
- 修改前后九张既有目标 BCH 图的 figure-data 数值：一致，Stage15 checker PASS。
- Stage15：50 图 PASS；Stage16 顶层清单、SHA 和最终 Gate：PASS。
- 未修改：BCH/CC Formal 原始 CSV、性能统计、交织/信道算法、CC 图、LDPC 参考、时延、推荐排名和用户手动更新的 `06_six_positions_fer/readme.txt` 内容。

## Git 状态

开始本轮时 HEAD 为 `ad6906135caa1a1c91c3cdfa2e8bcc7ac241f53b`，分支为 `S7-Comparision`。本轮未 commit、未 push、未合并 main。
