# BCH S2 Batch 1

依赖顺序：S2-01 → S2-02 → S2-03 → S2-04。任一依赖 Stage 阻塞立即停止。
批次仅完成固定多径 + 已知信道 MMSE，并输出下一阶段决策报告；不自动进入
S2-05～S2-09，不合并 main。

最终 Gate：`PASS_BCH_S2_BATCH1_FIXED_MULTIPATH_MMSE`
