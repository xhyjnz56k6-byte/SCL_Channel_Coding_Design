# Round06-D 图—数据—生成源内部映射

| 指定图或图组 | 直接对应 CSV | 正式上游 CSV | 生成脚本 | 中文重绘适用性 |
|---|---|---|---|---|
| Stage10 `stage10_traceback_fer.png` | `stage10_traceback_fer_figure_data.csv`（仅有限深度） | `stage10_traceback_study_results.csv`（含完整回溯） | `process_stage10_revision.py` | 适合；正文重绘从正式总表补齐完整回溯 |
| Stage10 `stage10_traceback_cpu_latency.png` | `stage10_traceback_cpu_latency_figure_data.csv` | `stage10_traceback_study_results.csv` | `process_stage10_revision.py` | 适合 |
| Stage11 三码率量化 FER 图 | 三个 `stage11_*_quantization_fer_figure_data.csv` | `stage11_soft_quantization_results.csv` | `process_stage11_revision.py` | 适合；包含 Float、Q3--Q8 |
| Stage13 九张 W/S/D FER 图 | 九个 `figure_data/stage13_*_{windowbits,slidebits,dtb}_fer_snr.csv` | `stage13_full_wsd_formal_results.csv` | `process_stage13_full_wsd.py` | 适合；按变量合成三张三码率图 |
| Stage14 十二张 BER/FER 图 | 十二个 `figure_data/stage14_*_{hard,soft}_{ber,fer}_by_organization.csv` | `stage14_online_slot_formal_results_all_decisions.csv` | `process_final_delivery.py` | 适合；合成四张三码率图 |
| Stage14 hard goodput 图 | `figure_data/stage14_hard_goodput_by_rate_and_organization.csv` | `stage14_online_slot_formal_results_all_decisions.csv` | `process_final_delivery.py` | 可重绘，正文篇幅控制后列为附录候选 |
| Stage15 soft goodput 图 | `figure_data/stage15_slot_soft_goodput.csv` | CSV 内 `sourceCsv` 指向 Stage14 正式总表 | Stage15 `process_final_delivery.py` | 适合；正文称归一化有效吞吐率 |

字段核对：Stage10 的 `dtb/rateCase/snrDb/FER/relativeFerIncreaseVsBlock/avgDecodeTimeUs/totalDecoderMemoryBytes/firstDecisionDelaySymbols/tracebackOperations` 均在正式总表中；Stage14 的 `BER/FER/firstOutputDelaySymbols/avgDecisionDelaySymbols/p95DecisionDelaySymbols/maxDecisionDelaySymbols/fullFrameLastDecisionSymbol/normalizedGoodput/organization/decisionMode/rateCase` 均在正式总表中。正式表没有名为 `successfulDecodeThroughput` 的独立列，报告采用已冻结的 `normalizedGoodput`，未臆造字段。
