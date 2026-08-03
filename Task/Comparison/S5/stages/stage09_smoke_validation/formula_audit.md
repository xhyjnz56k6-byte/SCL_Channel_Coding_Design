# S5 公式审计

| formulaId/name | expression | physicalMeaning / units | C++ / MATLAB | fixedInput | reference/output | tolerance | status |
|---|---|---|---|---|---|---|---|
| BPSK | x=1-2b | Es=1 | `runChannel` / official CC fixture | b=0,1 | +1,-1 | exact | PASS |
| EsN0 sigma | σ²=1/(2·10^(γ/10)) | 每实维噪声方差 | `sigmaSquaredFromEsN0` | γ=1,3.5,6 dB | 0.39716411736214075, 0.22334179607548157, 0.125594321575479 | 1e-12 | PASS |
| complex noise | n=σ(zI+jzQ) | zI,zQ 独立 N(0,1) | `complexNoise` | N=1280 | 可复现且 I≠Q | exact/hash | PASS |
| AWGN LLR | L=2Re(y)/σ² | log P(b=0)/P(b=1) | `runChannel` | fixed fixture | MATLAB/Python checker | 1e-12/1e-10 | PASS |
| no-AWGN LLR | L=100·sign(Re(y)) | 冻结有限软度量 | `finiteSoft` | σ²=0 | ±100/0 | exact | PASS |
| actual rate | R=300/Ntx | payload/transmitted | `schemeSpecs` | 459,612,480,640 | 0.65359477,0.49019608,0.625,0.46875 | 1e-15 | PASS |
| EbN0 | Eb/N0=Es/N0-10log10(R) | 仅报告转换 | `ebN0FromEsN0` | 3 dB,R=.5 | 6.010299956639812 dB | 1e-12 | PASS |
| multipath norm | h=[1,.65,.35]/sqrt(1+.65²+.35²) | sum h²=1 | `runChannel` | norm=1.2429802894656055 | energy=1 | 1e-12 | PASS |
| real MMSE | A=(HᵀH+σ²I)⁻¹Hᵀ | 已知实轴线性 MMSE | `multipathReceiver` | fixed fixture | Cholesky解 | 1e-10/1e-9 | PASS |
| gk/vk | gk=1-σ²Ckk; vk=σ²Ckk·gk; L=2gk xhat/vk | 对角高斯近似 | C++ / MATLAB | fixed fixture | MATLAB LLR复算 | 1e-10/1e-9 | PASS |
| CFO | φk=(π/6)k/(N-1) | 0°→30° | C++ / MATLAB | 四种 Ntx | 首末端点与旋转 | 1e-12/1e-10 | PASS |
| Doppler | εk=2/[3(N-1)]·(k/(N-1)-.5); φk=φk-1+2πεk-1 | 单径线性时变频偏相位 | C++ / MATLAB | 四种 Ntx | 完整 ε/φ trace | 1e-12/1e-10 | PASS |
| blockage | L=round(.10N), blocked LLR=0 | 已知连续擦除 | C++ / MATLAB | frame0..9 | mask/LLR | exact | PASS |
| burst | β=sqrt(10^(ISR/10)/2) | 复干扰总功率/符号功率 | `burstBeta` / MATLAB | ISR=10 dB | sqrt(5) | 1e-12 | PASS |
| BER/FER | BER=bitErr/(300F), FER=frameErr/F | payload可靠性 | runner/checker | grid | 264 点 CSV 由整数计数反算 | 5e-6 CSV显示容差 | PASS |
| paired stop | 双方 F 同步；min=1000,target=200,max=50000 | 公平停止 | runner/checker | grid | 同组同点 frameCount 相等 | exact | PASS |
| Wilson Gate | 复杂信道与 AWGN 的 FER 差大于双方 Wilson 95% 半宽之和 | smoke 可区分性 | `assess_grid_gate.py` | 10 个复杂信道/公平组 | 全部存在显著点 | margin>0 | PASS |

多径 `gk/vk` 近似忽略均衡输出间相关性；该限制必须保留在 known issues，不能用任意 LLR 缩放掩盖。
