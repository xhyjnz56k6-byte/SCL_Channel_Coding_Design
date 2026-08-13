S7 Chapter 9 evidence and report-data audit outputs.

Report-specific generated files:
- chapter9_report_2_5_percent_filter.csv
- chapter9_writing_evidence_coverage.csv
- report_table_data_9_1.csv
- report_table_data_9_10.csv
- report_table_data_9_11.csv
- report_table_data_9_12.csv
- report_table_data_9_2.csv
- report_table_data_9_3.csv
- report_table_data_9_4.csv
- report_table_data_9_5.csv
- report_table_data_9_6.csv
- report_table_data_9_7.csv
- report_table_data_9_8.csv
- report_table_data_9_9.csv

Sources:
- C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage10_bch_formal\results\formal_results.csv
- C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\stage11_cc_formal\results\formal_results.csv
- Stage12-Stage15 validated derived assets under C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7
- C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design\Task\Comparison\S7\S7_coding_reference_summary.csv

Purpose:
- Freeze which Stage15 figures may enter Chapter 9.
- Exclude dedicated 10 percent figures from the report without deleting experiment assets.
- Generate compact three-line-table source data for Tables 9.1-9.12.

Redrawing:
- No Stage15 figure is redrawn by this script.
- Mixed timing and tolerance figures are replaced by report tables.
- Table 9.9 recomputes frame-weighted CPU means from existing Formal rows after applying burstRatioRequested in {0.02, 0.05}.
- No interpolation, smoothing, or new experiment points are used.

Formal source hashes at generation time:
- BCH SHA-256: adbd8d2499b220525195fb115c989469ed00e0965d5f69ed6d28637f48ad4c9d
- CC SHA-256: 86f7ff8e46712406714887050d06de8ccd55e0c47ed7e6facd92c09556db886d

Filter:
- Formal report scope: burstRatioRequested in {0.02, 0.05}.
- Dedicated or mixed 0.10 result displays are not referenced.

No Formal simulation was rerun or modified. No commit, push, stage, or merge is performed by this generator.
