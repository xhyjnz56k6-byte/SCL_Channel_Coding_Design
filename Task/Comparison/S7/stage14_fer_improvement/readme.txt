阶段名称：stage14_fer_improvement
实验目的：计算 FER 改善、位置敏感性、突发容限和多指标推荐排名。
主要输入：Stage10/11 Formal、Stage12 全起点汇总、Stage13 时延复杂度汇总。
完成内容：744 行改善表、24 行目标 FER 表、8 行容限表和 6 行排名全部通过 checker。
主要输出：改善表、目标 FER 插值表、突发容限表、候选排名与推荐摘要。
当前结论：BCH 推荐 ROW_COLUMN rows=15；CC 综合推荐 PSEUDORANDOM span=128。
已知问题：NONE 基线未唯一包围目标 FER=0.5，因此不报告 Es/N0 改善；高工作点最坏起点多处饱和。
阶段状态：PASS
