# MATLAB官方卷积码独立验证

- MATLAB版本：24.2.0.2712019 (R2024b)
- 官方函数：poly2trellis、convenc、vitdec
- 固定向量：仅共享原始payload；MATLAB独立编码、打孔和译码。
- 统计验证：独立payload seed、AWGN seed和擦除位置seed。
- 母码长度：612；R2/3发送长度：459；打孔模式：[1 1 0 1]。
- 固定向量无噪声译码：PASS。
