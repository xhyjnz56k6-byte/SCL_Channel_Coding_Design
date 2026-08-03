# Validation report

Stage：`s5_stage05_cfo_channel`

四种 Ntx 的 0°/30° 端点、复旋转和完整 fixed trace 通过。

- Build：MinGW Release，PASS。
- Unit test：`s5_unit_tests`，PASS。
- Fixed-vector C++：PASS（Stage09 总记录）。
- Python fixed checker：PASS（Stage09 总记录）。
- MATLAB reference：PASS（Stage09 总记录）。
- Functional Gate：`PASS_S5_CFO`。
- Audit Gate：`NOT_RUN_NO_COMMIT_AUTHORIZATION`；用户未授权 commit/push，未伪造 functional range。
