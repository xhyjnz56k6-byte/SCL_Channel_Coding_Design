# stage03_noiseless 验证报告

最终 Gate：`PASS_STAGE03_NOISELESS`

- Release 构建：PASS。
- CTest：1/1 PASS。
- 8 Case × 1007 帧，共 8056 帧完整执行。
- 固定/边界样本：56 帧。
- 确定性随机帧：8000 帧。
- payloadErrorBits、payloadErrorFrames：0。
- decoderFailureFrames、miscorrectionFrames、undetectedErrorFrames：0。
- `trueSuccessFrames=totalFrames`：8/8 Case。
- BER、FER：全部 0。
- C++/MATLAB R2024b 固定样本编码 mismatch：0/8。
- C++/MATLAB payload 恢复 mismatch：0/8。

MATLAB 对分块 BCH 使用既有独立参考；对整块和双块方案使用 Communications Toolbox
官方 `bchenc/bchdec`，按 stage02 冻结的 shortening 和 block reassembly 执行。

首次构建因随机 payload 容器元素类型不同而失败；增加 stage03 局部显式转换后，
第二次从构建到 checker 完整重跑通过，未进入 stage04。

- functional base：`be243bec3672584792c6486766a89b4795aa8cc3`
- functional content：`edca1e4886c926edcbb2bd788cb2f57acdffeeae`
- 修改范围仅为 stage03 目录。
- 本地生成 `results/` 未进入 functional commit。
- push 未获授权；`main` 未合并。
