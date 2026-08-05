# Stage03 验证报告

- CMake/MinGW Release-like O2 编译：PASS。
- CTest `s7_unit_tests`：PASS。
- CODEBLOCK D=4/8/16/19、ROW_COLUMN rows=4/8/15/19、NONE、GLOBAL 全部置换合法且正逆一致：PASS。
- 非法 BCH depth=3 被拒绝：PASS。
- permutation SHA256 长度与 C++/MATLAB hash 一致：PASS。

Gate：PASS_BCH_INTERLEAVERS。

