# Commands Used

## Pre-Checks

1. `git status --short --branch`
   - Result: branch `stage02-03-common-foundation`; user-preserved workspace changes remain unstaged.
2. `git log -5 --oneline --decorate`
   - Result: Common-02 audit closure commit `fe6cfa0` was HEAD before Common-03 feature work.
3. `git diff --name-status fe6cfa0164afd097adb972a51afd73240105c188...6c304d0ef10fb7620c05ee1ef54b5d4a58f3fe00`
   - Result: 5 added Common-03 files; no BCH/CC/LDPC paths.

## Implementation And Validation

1. `apply_patch`
   - Result: added Common-03 C++ frame-pool header, Python generator/checker/build script, and C++ tests.
2. `python Task\Common\scripts\check_common03.py`
   - Result: initial failures exposed a root path issue, unordered JSON shard parsing, and checker self-scan markers.
3. `apply_patch`
   - Result: fixed root resolution, order-independent shard parsing, and later-stage marker scan scope.
4. `python Task\Common\scripts\check_common03.py`
   - Result: `COMMON-03 CHECK: PASS`; `Gate: PASS_COMMON_FRAME_POOL`.
5. `python Task\Common\scripts\build_common03.py`
   - Result: `COMMON-03 BUILD: PASS`.
6. `Task\Common\build\stage03\test_common03_frame_pool.exe Task\Common\build\stage03\pool_a\k200\manifest.json Task\Common\build\stage03\pool_a\k300\manifest.json`
   - Result: `COMMON-03 TEST PASS`.
7. `python Task\Common\scripts\check_common02.py`
   - Result: after restoring Common-02 snapshot-owned files byte-for-byte, `COMMON-02 CHECK: PASS`; `Gate: PASS_COMMON_TYPES_INTERFACES`.
8. `apply_patch`
   - Result: updated Common-02 checker range validation to use Common-02 `baseCommit...auditedContentCommit`, avoiding false failures after Common-03 files are committed.
9. `Copy-Item Task\Common\scripts\check_common02.py Task\Common\stages\stage02_common_types_interfaces\snapshot\scripts\check_common02.py -Force`
   - Result: synchronized the Stage02 checker snapshot.
10. `python Task\Common\scripts\check_common02.py`
    - Result: `COMMON-02 CHECK: PASS`; `Gate: PASS_COMMON_TYPES_INTERFACES`.
11. `python Task\Common\scripts\check_common03.py`
    - Result: `COMMON-03 CHECK: PASS`; `Gate: PASS_COMMON_FRAME_POOL`.

## Feature Commit

1. `git add -- Task/Common/include/common/frame_pool.hpp Task/Common/scripts/build_common03.py Task/Common/scripts/check_common03.py Task/Common/scripts/generate_common03_frame_pool.py Task/Common/tests/stage03/test_common03_frame_pool.cpp`
2. `git commit -m "common03: add deterministic frame pool foundation"`
   - Result: `6c304d0ef10fb7620c05ee1ef54b5d4a58f3fe00`.

## Audit Closure Procedure

The final audit commit SHA is intentionally not embedded in this file to avoid self-reference.

1. Generate `Task/Common/stages/stage03_common_frame_pool/changes.patch` from `fe6cfa0...6c304d0`.
2. Run `python Task\Common\scripts\check_common03.py`.
3. Run `python Task\Common\scripts\check_common02.py`.
4. Stage explicit Common-03 audit files.
5. Commit with `common03: record frame pool audit closure`.
6. Push `stage02-03-common-foundation`.
