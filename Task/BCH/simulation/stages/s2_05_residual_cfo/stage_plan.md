# s2_05_residual_cfo

## 目标

复基带 CFO、理想补偿验证与无补偿敏感性。

## 非目标

不修改 BCH 核心编译码器；不重跑 AWGN 或固定多径 formal；不引入交织、软判决 BCH、卷积码或 LDPC。

## 范围

仅限 Task/BCH 本 Stage 的信道基础、runner、脚本、测试、小型结果、科研绘图和审计记录。

## 接口与数据

统一使用 sourcePayloadEbN0Db、frameRate、snrDb；snrDb=sourcePayloadEbN0Db+10*log10(frameRate)，Bn=Rs；noisePolicyVersion=2。

## Gate

必须通过正向、负向、统计恒等式和数据审计后才发布 Gate。
