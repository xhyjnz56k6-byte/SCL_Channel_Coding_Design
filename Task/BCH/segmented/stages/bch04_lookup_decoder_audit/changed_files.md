# BCH-04 文件清单

功能范围 `ea43bc1...eb87765` 新增或修改：

- `Task/BCH/segmented/current/include/bch_segmented/bch15_lookup_decoder.hpp`
- `Task/BCH/segmented/current/src/bch15_lookup_decoder.cpp`
- `Task/BCH/segmented/current/tests/test_bch15_lookup_decoder.cpp`
- `Task/BCH/segmented/current/CMakeLists.txt`
- `Task/BCH/segmented/config/bch15_multi_error_seeds.csv`
- `Task/BCH/segmented/scripts/check_bch04_lookup_decoder.py`
- `Task/BCH/segmented/stages/bch04_lookup_decoder_audit/no_error_summary.csv`
- `Task/BCH/segmented/stages/bch04_lookup_decoder_audit/single_error_summary.csv`
- `Task/BCH/segmented/stages/bch04_lookup_decoder_audit/double_error_audit.csv`
- `Task/BCH/segmented/stages/bch04_lookup_decoder_audit/multi_error_seed_audit.csv`
- `Task/BCH/segmented/stages/bch04_lookup_decoder_audit/status_summary.csv`
- `Task/BCH/segmented/stages/bch04_lookup_decoder_audit/test_summary.csv`

审计范围另增加本目录的审计文档与真实 `changes.patch`；不修改 `Task/Common`。
