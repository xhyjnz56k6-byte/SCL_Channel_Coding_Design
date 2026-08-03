阶段名称：stage12_known_erasure_cc_validation
实验目的：独立验证Stage10中卷积码R1/2与R2/3在5%已知连续擦除下FER接近1的现象，重点复核R2/3。
验证手段：参数审计、固定trace、C++最小擦除比例扫描、MATLAB官方独立链路、17×27块交织诊断、C++/MATLAB统计比较。
固定向量：仅共享原始payload；C++和MATLAB独立编码、打孔、译码，母码、发送位、无噪声payload逐bit一致。
统计验证：C++和MATLAB使用独立payload seed与AWGN seed，仅比较BER、FER、置信区间和趋势。
实验边界：正确性验证，不属于新S5 Formal；MATLAB不替代Stage10结果；交织仅为diagnostic_only。
阶段状态：PASS_STAGE12_KNOWN_ERASURE_CC_VALIDATION
