阶段：Stage05 - MATLAB 官方参考验证

目的：以 MATLAB 的 poly2trellis、convenc、vitdec 对 C++ 卷积码链路作独立验证，防止仅靠同一实现自测造成系统性错误。

作用：检查完整 64 状态 Trellis、300 bit 编码与零尾、Hard/Soft/LLR 输入约定和比特顺序，并为测试向量和哈希提供可追溯依据。

得到的结果：128 条 Trellis 分支、16 个 300 bit 向量及 Hard/Soft/LLR 解码均无 mismatch，Gate 为 PASS_STAGE05_CC_MATLAB_REFERENCE。

主要文件：matlab/stage05_matlab_reference.m 是 MATLAB 参考；scripts/run_and_check_stage05.py 是运行与检查入口；results/stage05_matlab_reference_comparison.csv、cpp_trellis.csv、cpp_vectors.csv 和 hashes.json 保存证据。

交付关系：如老师要求“与 MATLAB 对比”，上传本目录的 comparison.csv 和 MATLAB 脚本；否则它属于支撑性验证材料。
