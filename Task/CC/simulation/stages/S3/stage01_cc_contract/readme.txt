阶段：Stage01 - 卷积码公共规格冻结

目的：为 S3 的所有仿真先固定同一套数学和数据定义，避免后续各阶段在比特顺序、状态编号、SNR 定义、打孔相位或结果字段上各自解释。

作用：定义 300 bit 电文、K=7、171/133(oct) 卷积码、R=1/2 母码与 R=2/3、3/4 打孔码的共同合同；同时冻结 BPSK 映射、AWGN 方差、BER/FER、吞吐和时延字段。后续 Stage02 至 Stage15 都以本合同为接口基准。

得到的结果：合同检查及故意破坏合同的负向检查均通过，Gate 为 PASS_STAGE01_CC_CONTRACT。它不产生性能曲线，但保证后续曲线和 CSV 可以公平比较。

主要文件：stage_plan.md 说明冻结项；results/stage01_cc_contract_check_results.csv 记录合同检查；scripts/check_stage01_contract.py 与 scripts/check_stage01_audit.py 用于复核。

交付关系：这是审计和复现基础，一般不作为老师要求的性能结果单独上传；上传最终结果时保留即可。
