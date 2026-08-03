# S5 Stage01～Stage09 执行报告

## 结论

当前分支 `S5-Compare` 已完成 Stage01～Stage09 功能实现和 smoke 验证，功能 Gate 为 `PASS_S5_SMOKE`。Formal 参数已冻结但未执行；本轮按授权停止在 Stage10 之前。

## 实现范围

- 四方案：`CC_R23_BLOCK_FLOAT`、`LDPC_BG2_N480_NMS`、`CC_R12_BLOCK_FLOAT`、`LDPC_BG2_N640_NMS`。
- 六信道：AWGN、固定实系数三径、CFO 30°、单径线性时变频偏相位、10% 已知连续擦除、5%/10 dB 未知连续突发干扰。
- 在线复噪声：`s5_complex_pair_v1`；Common-04 未修改，未生成 50000 帧完整复噪声池。
- 突发标度：`beta=sqrt(10^(ISR_dB/10)/2)`；10 dB 时 `sqrt(5)`。
- 多径：`A=(H^T H+sigmaSquared I)^(-1)H^T`，LLR 为 `2*gk*xhatk/vk`。
- 无 AWGN fixed vector：有限 `±100`，没有除零。

## 实际验证

- MinGW Release build：PASS。
- CTest `s5_unit_tests`：PASS。
- Fixed vector：2160 组合；身份无损模式零错误；完整逐符号 trace。
- Common frame pool：实际读取 K300 manifest/shard，frame 0～9 与 fixed fixture 一致。
- MATLAB：官方 `poly2trellis/convenc/vitdec` 的 CC R1/2、R2/3 编译码零 mismatch；六信道公式参考 PASS。
- Grid smoke：264 个唯一 scheme-point、7,929,674 个方案帧、NaN/Inf=0；所有公平配对 frameCount 一致。
- 四 shard 合并：PASS；BER/FER 整数计数反算和停止原因：PASS。
- 科学 Gate：两公平组/六信道联合动态范围 PASS；所有复杂信道/公平组相对 AWGN 至少有一个 Wilson 95% 可区分点。

关键生成资产：

- fixed trace SHA256：`ade41f60d95759f8ffca2c62a9355fd0e4fe1a16957756ad3e0beabbe4eea1d7`；
- grid summary SHA256：`0655ef9ea3da4a1a2dca0c4ecd891bcfbc7dd0d6c357aa4a7b74fa5c9ab00338`；
- grid Gate report SHA256：`fabe62a76d9aaa438813ea31415ee4e4529ef8698c75b7f16b6f3b591fa75997`；
- frozen Formal config SHA256：`ba5deca66b8cbd3fbc5f4cbc0457a158946243fd530562f17d33b638b64b1047`。

## 已知问题与解释边界

- 10% 已知连续擦除下，两条 CC 曲线在 1～6 dB 均 `FER>=0.99`；对应 LDPC 曲线未共同饱和，故比较组仍有动态范围。该现象作为告警保留，不调整已批准参数。
- 多径逐符号对角高斯 LLR 忽略均衡输出间相关性。
- 遮挡结论只适用于理想已知连续擦除；突发 mask 对接收端未知；两者均无交织。
- 多普勒只能称为“单径线性时变频偏相位模型”，不是实际卫星多普勒模型。

## Git 与审计状态

- 所有新增内容位于 `Task/Comparison/S5/`；未修改 BCH、CC、LDPC、Common。
- 未获得 commit/push 授权，所以没有功能提交 SHA，也未伪造 Stage functional range；各 manifest 将审计 Gate 记录为 `NOT_RUN_NO_COMMIT_AUTHORIZATION`。
- 未 push，未合并 `main`，未进入 Formal。
