# Commands Used

Commands are recorded in execution order.

1. `git branch --show-current`
   - Result: `stage02-03-common-foundation`.
2. `git status --short --branch`
   - Result: user-preserved deletes under `初始规划/` and untracked `Task/Common/Plan/`; neither will be staged.
3. `git log -1 --oneline`
   - Result: `dba843f stage01: record common definition repair metadata`.
4. `git remote -v`
   - Result: origin points to GitHub repository.
5. Required Common-01 files and docs were read.
6. `g++ --version`
   - Result: `g++ 15.2.0` available.
7. `apply_patch`
   - Result: added Common-02 C++ headers, source, and test.
8. `apply_patch`
   - Result: added Common-02 build and check scripts.
9. Snapshot copy commands
   - Result: copied headers, source, test, scripts, and CMake into snapshot.
10. `apply_patch`
    - Result: added Stage02 audit files.
11. `python Task\Common\scripts\build_common02.py`
    - Result: `COMMON-02 BUILD: PASS`.
12. `python Task\Common\scripts\check_common02.py`
    - Result: initial fail because the script scanned its own forbidden marker constants and the rate misuse coverage was implicit.
13. `apply_patch`
    - Result: limited forbidden marker scan to C++ headers/tests and made codecInputLength rate misuse coverage explicit.
14. `python Task\Common\scripts\check_common02.py`
    - Result: `COMMON-02 CHECK: PASS`; `Gate: PASS_COMMON_TYPES_INTERFACES`.
15. `git add <explicit Common-02 paths>`
    - Result: staged only Common-02 files; did not stage `Task/Common/Plan/`, `Task/Common/build/`, preserved `初始规划` deletes, or BCH/CC/LDPC paths.
16. `git diff --cached -- Task/Common ':!Task/Common/stages/stage02_common_types_interfaces/changes.patch' | Set-Content -Encoding UTF8 Task\Common\stages\stage02_common_types_interfaces\changes.patch`
    - Result: generated Stage02 review patch from staged diff.
17. `python Task\Common\scripts\check_common02.py`
    - Result: final pre-commit check PASS.
18. `git commit -m "common02: add common types and interface skeleton"`
    - Result: created commit `290b868b85513398f34a5c153c39ad8f409a55a3`.

Final build, validation, commit, and push commands are appended after execution.
