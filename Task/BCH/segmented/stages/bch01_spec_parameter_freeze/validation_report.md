# BCH-01 validation report

## Executed evidence

Initial branch identity was `bch-01-spec-parameter-freeze`; its initial working tree was clean and both `HEAD` and `main` resolved to `80bfe5d61d11aa62fe69e91f24dd1dbad4efb164`. The Git workflow, BCH plan files, `Task/Common/CMakeLists.txt`, Common source inventory, and all required Common public headers were inspected. The verified mappings are recorded in `common_interface_audit.md`.

## Actual validation

| Check | Command or method | Result |
|---|---|---|
| Existing binary regression | Existing executables `test_common04_random_policy`, `gaussian_noise`, `modulation_awgn`, `metrics_control`, `checkpoint`, and `integration` | PASS (all six exit code 0) |
| MinGW CMake configure | `cmake -G "MinGW Makefiles" -S Task/Common -B Task/BCH/segmented/build/bch01_common_config_only -DCMAKE_BUILD_TYPE=Release` | PASS |
| Full source build | Optional `cmake --build Task/BCH/segmented/build/bch01_common_config_mingw` | TIMEOUT / NOT PROVEN; excluded from PASS evidence |
| CSV syntax | Python `csv.reader`, non-empty records only, fixed-width assertion | PASS |
| JSON syntax | Python `json.loads(manifest.json)` | PASS |
| Forbidden scope | `git status --porcelain`, all paths constrained to `Task/BCH/` | PASS |
| Diff whitespace | `git diff --check` | PASS |
| No implementation | scan for BCH C/C++ sources excluding generated `build/` | PASS |

The default CMake generator selected unavailable NMake. A subsequent MinGW configure succeeded. The full source build is explicitly `TIMEOUT / NOT PROVEN`, not PASS. No MATLAB command was run by design.

## Gate

`PASS_BCH01_SPEC_PARAMETER_FREEZE_FINALIZED` after the final metadata commit and successful push.
