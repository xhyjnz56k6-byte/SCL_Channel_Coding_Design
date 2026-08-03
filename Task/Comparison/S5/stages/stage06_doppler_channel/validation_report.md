# Validation report

Stage：`s5_stage06_doppler_channel`

瞬时频偏首负末正并过零；四种 Ntx 完整 epsilon/phase trace 与 MATLAB 旋转通过。

- Build：MinGW Release，PASS。
- Unit test：`s5_unit_tests`，PASS。
- Fixed-vector C++：PASS（Stage09 总记录）。
- Python fixed checker：PASS（Stage09 总记录）。
- MATLAB reference：PASS（Stage09 总记录）。
- Functional Gate：`PASS_S5_DOPPLER`。
- Audit Gate：`NOT_RUN_NO_COMMIT_AUTHORIZATION`；用户未授权 commit/push，未伪造 functional range。
