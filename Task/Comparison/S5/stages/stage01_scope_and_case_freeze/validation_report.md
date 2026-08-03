# Validation report

Stage：`s5_stage01_scope_and_case_freeze`

四方案、两组公平比较、分支和 Es/N0 语义已冻结。

- Build：MinGW Release，PASS。
- Unit test：`s5_unit_tests`，PASS。
- Fixed-vector C++：PASS（Stage09 总记录）。
- Python fixed checker：PASS（Stage09 总记录）。
- MATLAB reference：PASS（Stage09 总记录）。
- Functional Gate：`PASS_S5_SCOPE`。
- Audit Gate：`NOT_RUN_NO_COMMIT_AUTHORIZATION`；用户未授权 commit/push，未伪造 functional range。
