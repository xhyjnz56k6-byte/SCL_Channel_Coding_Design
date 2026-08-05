# S7 最终目录说明

```text
Task/Comparison/S7/
├─ current/                         C++ 实现、测试和 MATLAB 独立参考
├─ configs/                         Smoke/Formal 冻结配置
├─ scripts/                         选择、仿真分析、绘图和统一 checker
├─ stage00...stage09/               审计、规格、功能、Smoke 与 Prescan
├─ stage10_bch_formal/results/      BCH 主 Formal 原始 CSV
├─ stage11_cc_formal/results/       CC 主 Formal 原始 CSV
├─ stage12_all_start_scan/results/  BCH/CC 全起点原始与汇总
├─ stage13_latency_complexity/      时延和结构代价汇总
├─ stage14_fer_improvement/         FER 改善、容限和推荐排名
├─ stage15_scientific_plots/
│  ├─ results/bch/                  29 个当前有效 BCH 图目录（含 2%/5%全起点热力图与 BER 图）
│  ├─ results/cc/                   21 个当前有效 CC 图目录
│  └─ archive/                      失败或被替换图，仅供审计
├─ stage16_final_integration/       最终统一 Gate
├─ results/
│  ├─ bch/、cc/                     Formal 原始路径/SHA 引用
│  ├─ ldpc_baseline/                62 行不兼容独立历史参考
│  └─ summary/                      根级清单说明
├─ archive/                         顶层报告和清单历史版本入口
├─ S7_final_report.md               最终中文报告
├─ S7_metric_summary.csv            八配置核心指标
├─ S7_result_inventory.csv          正式结果索引
├─ S7_plot_inventory.csv            50 图索引
├─ S7_source_inventory.csv          源码/脚本/配置 SHA
└─ S7_sha256.txt                    非 build 当前资产 SHA
```

可用于最终结论：Stage10/11 Formal 原始 CSV、Stage12 当前全起点 CSV、Stage13/14 通过 checker 的派生表、Stage15 `results/` 当前图和根级清单。

仅用于 Smoke/参数选择：Stage08、Stage09；不得替代 Formal 曲线。

仅用于审计：任何 `archive/`、checkpoint 恢复预检和失败图版本；不得与当前结果混用。

历史复用：S6 LDPC N560 表只存于 `results/ldpc_baseline/` 独立参考，因信道不兼容不得进入 S7 交织排名或突发容限。

`build/`、可执行文件和 checkpoint 是生成资产，不进入功能提交或最终科研数据清单。
