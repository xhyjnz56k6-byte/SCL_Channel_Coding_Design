阶段：Stage08 - AWGN 预扫描

目的：在低成本仿真中为六个码率/判决组合定位瀑布区，确定 Stage09 正式仿真的 SNR 采样范围。

作用：先以 60 帧 smoke 粗定位 FER 约 0.5 的中心，再按 0.5 dB 形成联合 prescan 范围；Hard/Soft 在同码率下共享电文、编码和母噪声，保证公平。

得到的结果：六个 Case 的 smoke、逐点公式与停止条件检查均通过，生成 BER/FER 预扫描图、推荐正式范围和图文件清单，Gate 为 PASS_STAGE08_CC_AWGN_PRESCAN。

主要文件：src/stage08_awgn_prescan_runner.cpp 是仿真程序；scripts/run_stage08.py 和 plot_and_check_stage08.py 负责运行、绘图和检查；results/stage08_awgn_prescan_formal_recommendations.csv 是正式范围建议。

交付关系：这是选点工具。预扫描 PNG 仅供过程说明，最终提交应优先使用 Stage09 及 Stage15 的正式图。
