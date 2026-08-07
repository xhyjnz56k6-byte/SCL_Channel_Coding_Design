# Round05-A BCH 最终扫描报告

## 1. 范围与仓库状态

在 `S8-PaperDocu`、HEAD `d3f580f6` 上完成 BCH 定向扫描。起始工作区干净；只新增本目录，未修改算法、旧结果或第1～3章。

## 2. 正式 BCH 方案

冻结五个核心方案：S200、B200、S300、B300-390、B300-426。B300-390 是300 bit主基线；B300-426是 t=14 增强候选，两者都有正式数据，不能互相替代。

## 3. 正式源码链

分组链为 BCH(15,11) 系统编码+syndrome单错查表+后验校验；整块链为缩短系统 BCH+BM+Chien+后验 syndrome；统一 adapter 区分 true/reported/miscorrection/failure。

## 4. S1 正式结果

数值主表为报告冻结的 W8 五方案数据；正式 Es/N0 中文图与修复后软件时延来自 W9。旧四方案 formal 树降为历史审计。

## 5. S2 模型与结果

当前源码可完整冻结5条正式线：AWGN、固定多径+已知信道MMSE、帧内线性相位漂移（0°到30°）、随机短时矩形遮挡、AWGN后连续硬比特反转及交织比较。逐信道 MASTER 分别为 Stage07、08、10、12、16。旧固定初相位专题只作附录验证。

## 6. 数据质量与版本冲突

1890行正式主数据的计数、BER/FER、状态和码率全部通过；W9图源222行转换通过。Stage07/08 的 `snrDb` 是 `2Es/N0`，比报告 Es/N0 高3.0102999566 dB，必须只转换横轴后再用于正文。Stage17最终全信道Gate因 whitespace check未通过，故不做全信道严格排名。

## 7. 第4章可直接使用材料

正式参数表、S1两张FER主图、逐信道模型定义、Stage10/12/16图候选、数据来源和结论草案均已整理到 `report_materials`。Stage07/08原PNG需轴转换后使用。

## 8. Gate

Gate A/B/C/D/E/H/I：PASS；Gate F：PASS_WITH_INTEGRATION_LIMITATION；Gate G：PASS_WITH_AXIS_CONVERSION_REQUIRED。无需要修改算法或重跑formal的 BLOCKING 问题。

建议：可以开始第4章参数、算法和逐信道分析正文；在插入 Stage07/08 主图前先完成非覆盖式 Es/N0 横轴转换。不得声称已完成全信道最终排名。
