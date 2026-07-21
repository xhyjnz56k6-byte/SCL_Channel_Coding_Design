# Commands Used

Commands are recorded in execution order for the Common-02 content and audit closure work.

## Initial Common-02 Content Commit

1. `git branch --show-current`
   - Result: `stage02-03-common-foundation`.
2. `git status --short --branch`
   - Result: user-preserved deletes under `初始规划/` and untracked `Task/Common/Plan/`; neither was staged.
3. `git log -1 --oneline`
   - Result: Common-01 was present on `main`.
4. `g++ --version`
   - Result: `g++ 15.2.0` available.
5. `python Task\Common\scripts\build_common02.py`
   - Result: `COMMON-02 BUILD: PASS`.
6. `python Task\Common\scripts\check_common02.py`
   - Result after fixes: `COMMON-02 CHECK: PASS`; `Gate: PASS_COMMON_TYPES_INTERFACES`.
7. `git commit -m "common02: add common types and interface skeleton"`
   - Result: `290b868b85513398f34a5c153c39ad8f409a55a3`.

## Audit Repair Pre-Checks

1. `git status --short --branch`
   - Result: branch is `stage02-03-common-foundation`; user-preserved workspace changes remain unstaged.
2. `git log -5 --oneline --decorate`
   - Result: `9d0debb` audit metadata commit is HEAD; `290b868b` Common-02 content commit is present.
3. `git rev-parse main`
   - Result: `dba843f535d3a678f684300f10731f1cbd19a406`.
4. `git rev-parse HEAD`
   - Result before this repair commit: `9d0debbd7fc0a59ccded49525817e7363aead5f0`.
5. `git merge-base main HEAD`
   - Result: `dba843f535d3a678f684300f10731f1cbd19a406`.
6. `git diff --name-status main...290b868b85513398f34a5c153c39ad8f409a55a3`
   - Result: 32 added Common-02 files; no BCH/CC/LDPC paths.
7. `git ls-files Task/Common/Plan`
   - Result: no tracked files.
8. `git status --short Task/Common/Plan Task/Common/build Task/BCH Task/CC Task/LDPC`
   - Result: `Task/Common/Plan/` and `Task/Common/build/` are untracked; BCH/CC/LDPC have no status output.

## Audit Repair Edits

1. `apply_patch`
   - Result: strengthened `Task/Common/scripts/check_common02.py`.
2. `Copy-Item Task\Common\scripts\check_common02.py Task\Common\stages\stage02_common_types_interfaces\snapshot\scripts\check_common02.py -Force`
   - Result: synchronized the checker snapshot.
3. `apply_patch`
   - Result: refreshed manifest, commit metadata, validation report, changed-files report, command log, and known-issues report.
4. `git diff dba843f535d3a678f684300f10731f1cbd19a406...290b868b85513398f34a5c153c39ad8f409a55a3 -- Task/Common ':!Task/Common/stages/stage02_common_types_interfaces/changes.patch'`
   - Result: regenerated `Task/Common/stages/stage02_common_types_interfaces/changes.patch`.

## Audit Repair Validation

1. `python Task\Common\scripts\check_common02.py`
   - Result: first audit repair run failed only because the snapshot checker SHA was intentionally stale.
2. `python Task\Common\scripts\check_common02.py`
   - Result: `COMMON-02 CHECK: PASS`; `Gate: PASS_COMMON_TYPES_INTERFACES`.
3. `python Task\Common\scripts\build_common02.py`
   - Result: `COMMON-02 BUILD: PASS`.
4. `Task\Common\build\stage02\test_common02_types_interfaces.exe`
   - Result: `COMMON-02 TEST PASS`.

## Commit And Push Procedure

These commands are the closure procedure for this audit repair. The final audit
commit SHA is intentionally not embedded in this file to avoid self-reference.

1. `git add <explicit Common-02 audit repair paths>`
2. `git commit -m "common02: finalize audit chain and validation coverage"`
3. `git push origin stage02-03-common-foundation`
4. `git rev-parse origin/stage02-03-common-foundation`
5. `git ls-remote origin refs/heads/stage02-03-common-foundation`
