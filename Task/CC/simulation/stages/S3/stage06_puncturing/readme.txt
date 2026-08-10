阶段：Stage06 - 打孔与多码率兼容

目的：在 R=1/2 母码基础上实现并验证 R=2/3、R=3/4 打孔方案，满足老师要求的三种卷积码率比较。

作用：处理打孔掩码、去打孔中性软信息、真实传输长度、零尾末尾和连续编码时的跨时隙打孔相位。它让所有后续实验都能以同一母码切换速率。

得到的结果：打孔模式通过无噪声、固定 AWGN 预扫和 MATLAB pattern 对照；最终被后续实验使用的整块有效长度为 R12=612、R23=459、R34=408 bit，Gate 为 PASS_STAGE06_CC_PUNCTURING。

主要文件：scripts/run_stage06.py 是执行入口；matlab/stage06_matlab_reference.m 是 MATLAB 对照；results/stage06_puncturing_selection.json 记录选定模式，comparison.csv 保存对照。

交付关系：最终报告必须体现三种码率，但不必上传此阶段的候选预扫表，除非老师要求打孔图样的技术附件。
