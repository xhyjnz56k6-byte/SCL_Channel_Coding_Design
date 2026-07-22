# BCH-04 查表译码器与误纠审计

## 范围

本 Stage 实现 BCH(15,11,1) 的 15 bit 单块查表译码：零 syndrome 的无错路径、单错定位翻转、翻转后的 syndrome 检查，以及对双错误纠行为的完整审计。

不包含 200/300 bit 分块适配、AWGN、BM、Chien 或 BCH-05 内容。

## 接口与状态

`decodeBch15Lookup(received, table)` 返回系统信息位、修正码字、修正前/后 syndrome、查表命中、位置和状态。`syndrome=0` 仅产生 `NO_ERROR`；非零命中且 post-syndrome 为零产生 `CORRECTED_SINGLE_ERROR`；未命中产生 `UNRECOGNIZED_SYNDROME`；命中但翻转后仍非零或表给出越界位置产生 `POST_CHECK_FAILED`。

## 验收矩阵

| 需求 | 实现位置 | 正向测试 | 负向测试 | Gate |
|---|---|---|---|---|
| 无错译码 | lookup decoder | 2048 合法码字 | 无 | 全部恢复 |
| 单错译码 | lookup decoder/table | 30720 单错 | 无 | payload、位置、post syndrome 全正确 |
| 表损坏防御 | lookup decoder | 15/100 越界条目 | 缺失/错误条目 | 无越界访问且状态正确 |
| 双错审计 | decoder test | 215040 模式 | 误纠分类 | 分类守恒、不隐藏误纠 |
| 固定多错样本 | seed fixture | 12 seed x 4 message | fixture 解析 | CSV 可复现 |

## Gate

`PASS_BCH04_LOOKUP_DECODER_MISCORRECTION_AUDIT` 要求无错、单错完全恢复，215040 双错分类完成且分类总数守恒，Common 未被修改或破坏。
