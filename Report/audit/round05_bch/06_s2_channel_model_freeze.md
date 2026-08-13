# S2 信道模型冻结

| formalName | modelFormula / parameters | receiverKnowledge / processing | runner | formalData | notes |
|---|---|---|---|---|---|
| AWGN 基准 | BPSK 后加实高斯噪声；Stage07 `sigma²=1/10^(waveformSnr/10)` | 零阈值硬判决后 BCH | `stage07_awgn_dense_formal_runner.cpp` | Stage07 dense results | 其 `snrDb=2Es/N0` 的 dB 表示，报告 Es/N0 需减 3.0102999566 dB |
| 固定实数多径+已知信道线性 MMSE | `h=[1,0.65,0.35]`，delay `[0,1,3]`，单位能量归一；`y=Hx+n`；`xhat=(H^T H+sigma²I)^-1 H^T y` | 接收端已知 h；带状 Cholesky；均衡后硬判决 | `bch_multipath_simulation.cpp`、`fixed_multipath_mmse.cpp`、Stage08 runner | Stage08 common-SNR results | 卷积观测长 N+3；噪声加在卷积后；横轴同样需减 3.0102999566 dB 才是 Es/N0 |
| 帧内线性相位漂移（末端30°、无补偿） | `phi[k]=k*pi/(6*(N-1))`；`r=x exp(j phi)+nI+j nQ` | 初相位0；末符号30°；接收端取实部硬判决；无相位/CFO补偿 | Stage09 validator、`stage10_cfo_formal_runner.cpp` | Stage10 dense results | 不是“固定30°相位”，也不应称真实多普勒；正式名按源码描述 |
| 随机短时矩形遮挡 | 调制符号域连续区间乘0；代表比例10%；每帧随机起点；不环绕；遮挡期仍叠加 AWGN | 无位置辅助恢复、无交织，直接硬判决和BCH译码 | `stage12_blockage_formal_runner.cpp` | Stage12 dense/ratio/fixed-length | 可称短时遮挡，不能写成软信息擦除 |
| AWGN+连续硬比特反转（含交织比较） | AWGN 硬判决后，在随机连续区间翻转 bit；K200代表12 bit，K300代表8 bit | 可选 NONE/块/行列/伪随机交织；去交织后BCH译码 | Stage13 core/simulation、Stage16 runner | Stage16 raw results | 与第9章交织专题共享证据但结论边界不同，不得混成一般信道排名 |

遗留 `batch2_corrected/published` 还含“固定初始载波相位灵敏度”和旧 residual-CFO 图。当前仓库没有与该固定初相位结果同级的正式源码链，故仅列 VALIDATION/SUPERSEDED，不作为当前 S2 MASTER。当前可由源码完整冻结的正式信道线为 5 条。
