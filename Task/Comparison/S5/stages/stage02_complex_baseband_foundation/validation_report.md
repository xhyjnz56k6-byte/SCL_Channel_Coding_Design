# Validation report

Stage：`s5_stage02_complex_baseband_foundation`

在线复噪声可复现，I/Q 独立；N=1280 通过；无噪声使用有限 ±100。

- Build：MinGW Release，PASS。
- Unit test：`s5_unit_tests`，PASS。
- Fixed-vector C++：PASS（Stage09 总记录）。
- Python fixed checker：PASS（Stage09 总记录）。
- MATLAB reference：PASS（Stage09 总记录）。
- Functional Gate：`PASS_S5_COMPLEX`。
- Audit Gate：`NOT_RUN_NO_COMMIT_AUTHORIZATION`；用户未授权 commit/push，未伪造 functional range。
