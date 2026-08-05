阶段名称：stage11_cc_formal
实验目的：执行 CC 四配置 Formal，并严格区分推荐工程配置与 128-step 等跨度受控对比。
主要输入：CC_NONE、SHORT_DEPTH_BLOCK D=8、PSEUDORANDOM span=128、SHORT_DEPTH_BLOCK D=16。
完成内容：已完成 31 个 Es/N0、3 个突发比例、6 个位置、4 个配置的全部 Formal 网格。
主要输出：2232 行 Formal CSV、checkpoint、checkpoint manifest、checker 报告和审计记录。
当前结论：558 个配对比较组全部通过 checker；D8 与 PSEUDO128 仅标记为“推荐工程配置对比”，D16 与 PSEUDO128 标记为等跨度 128 受控对比。
已知问题：工程推荐 D8 与 PSEUDO128 跨度不同，不允许解释为纯方法差异；CPU 时延依赖本机环境。
阶段状态：PASS

