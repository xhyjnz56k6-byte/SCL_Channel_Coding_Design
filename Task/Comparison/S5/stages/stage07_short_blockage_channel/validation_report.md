# Validation report

Stage：`s5_stage07_short_blockage_channel`

10% 长度、确定性相对起点、不回绕 mask、遮挡 LLR=0 通过。

- Build：MinGW Release，PASS。
- Unit test：`s5_unit_tests`，PASS。
- Fixed-vector C++：PASS（Stage09 总记录）。
- Python fixed checker：PASS（Stage09 总记录）。
- MATLAB reference：PASS（Stage09 总记录）。
- Functional Gate：`PASS_S5_BLOCKAGE`。
- Audit Gate：`NOT_RUN_NO_COMMIT_AUTHORIZATION`；用户未授权 commit/push，未伪造 functional range。
