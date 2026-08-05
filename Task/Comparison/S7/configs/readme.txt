阶段名称：stage02_parameter_freeze
实验目的：保存 S7 Smoke 与 Formal 冻结配置。
主要输入：S7_experiment_design_plan.md。
完成内容：已冻结主信道、编码、交织、随机性、停止和零值策略。
主要输出：s7_smoke_frozen_config.json、s7_formal_frozen_config.json。
当前结论：Formal 配置仅定义矩阵，authorized=false，不能用于启动 Stage10。
已知问题：Formal 参数将在 Stage09 候选排名后填入 selectedParameter。
阶段状态：PASS
