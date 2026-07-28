# Stage02 文件变更说明

功能提交 `4b268e385eda34c79352ca186a57985b7d93869a` 相对 Stage01 审计提交 `1cace054f06c0648bd6b2593c1b2430b92fd3d5f` 新增：

- CC 本地生成物忽略规则；
- 64×2 trellis 唯一实现；
- 可 reset/export/import 的连续编码状态接口；
- 300/200 bit 零尾整块编码器；
- Release CMake、C++ 单元测试和独立寄存器参考；
- MATLAB `poly2trellis`/`convenc` 对比脚本及真实结果；
- Stage02 计划、配置、命令和结果摘要。

功能文件仅位于 `Task/CC/.gitignore`、`Task/CC/shared/**`、`Task/CC/block/current/**` 和 Stage02 目录。未修改 Common、BCH 或 LDPC。

复跑发现摘要生成器会移除既有 MATLAB Gate 行，因此新增修复提交 `b79749d6b4e6fc5ef97ade3ac226078494e834f2`。该提交只修改 `scripts/build_and_test_stage02.py`，让它验证并稳定复现 4 个 MATLAB 固定向量和 128 条 trellis 比较结果。

审计提交增加本文件、`manifest.json`、`validation_report.md`、`changes.patch`、`git_commit.txt` 及 CC 统一审计 checker，不改变 trellis/encoder 行为。
