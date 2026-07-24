# Validation report

已执行并通过：核心 CMake/MinGW 构建、`test_bch_block`、无噪声集成、AWGN unit、W1 参数 checker、W2 codec checker、W3 MATLAB Communications Toolbox 对比、W5 smoke/prescan、W6 C++ formal、W8 多方案比较与绘图。

结果摘要：W6 BCH-B300-426 formal 共 9 个 Eb/N0 点、201669 帧；W3 参数/生成/编码/能力范围 mismatch 均为 0。

统一 Gate：`PASS_WITH_KNOWN_LIMITATION`。W7 MATLAB 官方逐帧 formal 对比尚未执行，因此不能声明完整跨实现 formal Gate PASS。

审计状态：本地功能与证据已收口；commit 和 push 在本次审计后完成，未合并 `main`。
