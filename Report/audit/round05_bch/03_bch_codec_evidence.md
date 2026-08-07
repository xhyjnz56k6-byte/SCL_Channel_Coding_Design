# BCH 编译码主链路证据

## 分组 BCH

主文件：`bch15_encoder.cpp`、`bch15_syndrome.cpp`、`bch15_lookup_table.cpp`、`bch15_lookup_decoder.cpp`、`bch15_segmented_adapter.cpp`。

流程：payload 末尾补零至 11 bit 整数块；逐块系统 BCH(15,11) 编码并拼接；接收端逐 15 bit 计算 syndrome；零 syndrome 直接通过，非零 syndrome 查单错表并翻转；翻转后重新校验 syndrome；恢复 11 bit 信息块、拼接并删除 filler。

整帧 `reportedSuccess` 要求所有子块均被译码器声明成功；`trueSuccess` 只由最终 payload 与原 payload 比较；filler-only 差异不构成 payload FER；声明成功但 payload 错误计为 `miscorrected`。查表失败或后验 syndrome 非零计为译码失败，但适配器仍保留可恢复 payload 供审计。

## 整块缩短 BCH

主文件：`bch_block.hpp`、`bch_block.cpp`。

流程：在 payload 前补已知零至母码信息长度；系统 BCH 编码；删除缩短前缀发送；接收端补回已知零，计算 2t 个 syndrome，执行 Berlekamp-Massey 和 Chien 搜索，翻转根位置并做后验 syndrome 检查，最后去掉缩短前缀恢复 payload。

- B200：GF(2^8)，primitive polynomial `0x11D`，t=6。
- B300/B300-426：GF(2^9)，primitive polynomial `0x211`，t=10/t=14。
- 失败状态区分 locator degree 超限、根数不匹配、根落在缩短前缀及后验 syndrome 非零。
- 复杂度记录 syndrome、BM、Chien、GF 运算与翻转计数；内存记录 GF 表和逐帧工作区。

## 统一适配器

`encodeBchFrame()` 按 Case 分派并核验编码长度；`decodeBchFrame()` 统一生成声明状态、失败状态、复杂度和内存；`auditDecodedBchFrame()` 生成 `trueSuccess` 与 `miscorrected`。

正文可以写“分组方案采用 syndrome 单错查表，整块方案采用 BM+Chien”；不得写“译码器声明成功等同于 payload 正确”，也不得把分组任一子块失败直接替代最终 payload FER 定义。
