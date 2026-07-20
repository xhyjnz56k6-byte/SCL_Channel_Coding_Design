# Commands Used

Commands are recorded in execution order with result summaries.

1. `git init`
   - Result: initialized an empty repository.
2. `git config --get user.name`
   - Result: user name configured.
3. `git config --get user.email`
   - Result: user email configured.
4. `git branch -M main`
   - Result: reported a transient HEAD lock error, but branch state later showed `main`.
5. `git status --short --branch`
   - Result: no commits yet on `main` before the user-created baseline.
6. User executed initial baseline commands externally:
   - `git add AGENTS.md discuss.md Task 初始规划 任务要求`
   - `git commit -m "initial project baseline"`
   - `git switch -c stage01-common-definition`
7. `git branch --show-current`
   - Result: `stage01-common-definition`.
8. `git status --short --branch`
   - Result: clean before Common-01 edits.
9. `git log -1 --oneline`
   - Result: `a3449db initial project baseline`.
10. `git remote -v`
    - Result: no remote configured.
11. `New-Item -ItemType Directory -Force Task\Common\config,Task\Common\docs,Task\Common\scripts,Task\Common\stages\stage01_common_definition\snapshot`
    - Result: created Common-01 directories.
12. `apply_patch`
    - Result: added JSON configuration files.
13. `apply_patch`
    - Result: added Markdown definition documents.
14. `apply_patch`
    - Result: added validation script.
15. `apply_patch`
    - Result: added Stage audit files.
16. `Copy-Item Task\Common\config\*.json Task\Common\stages\stage01_common_definition\snapshot\config\ -Force`
    - Result: copied frozen JSON definitions into snapshot.
17. `Copy-Item Task\Common\docs\*.md Task\Common\stages\stage01_common_definition\snapshot\docs\ -Force`
    - Result: copied frozen Markdown definitions into snapshot.
18. `Copy-Item Task\Common\scripts\validate_common01_definition.py Task\Common\stages\stage01_common_definition\snapshot\scripts\ -Force`
    - Result: copied validation script into snapshot.
19. `python Task\Common\scripts\validate_common01_definition.py`
    - Result: `COMMON-01 VALIDATION: PASS`; `Gate: PASS_COMMON_DEFINITION`.
20. `python Task\Common\scripts\validate_common01_definition.py --negative-tests`
    - Result: all seven negative mutations failed as expected; final validation PASS.
21. `python Task\Common\scripts\validate_common01_definition.py`
    - Result: final normal validation PASS after audit updates.
22. `git status --short --branch`
    - Result: on `stage01-common-definition`; `Task/Common/` is untracked.
23. `git diff --stat`
    - Result: no output because new files are untracked.
24. `git diff -- Task/Common`
    - Result: no output because new files are untracked.
25. `git ls-files --others --exclude-standard Task/Common`
    - Result: listed only Common-01 files and snapshot copies.
26. `git status --porcelain=v1 Task/BCH Task/CC Task/LDPC`
    - Result: no output; no BCH/CC/LDPC changes detected.
27. `git add Task/Common`
    - Result: staged only Common-01 files.
28. `git diff --cached --stat`
    - Result: 32 files, 3084 insertions, all under `Task/Common`.
29. `git diff --cached --name-only Task/BCH Task/CC Task/LDPC`
    - Result: no output; no out-of-scope staged files.
30. `git commit -m "stage01: freeze common definitions"`
    - Result: created commit `899c4c4`.
31. `git commit -m "stage01: record common definition commit metadata"`
    - Result: created commit `e76e5fb`.
32. `git push -u origin stage01-common-definition`
    - Result: pushed Stage branch to `origin/stage01-common-definition`.
33. `git push -u origin main`
    - Result: pushed base branch to `origin/main` so GitHub can compare `main...stage01-common-definition`.
34. `apply_patch`
    - Result: repaired checkpoint SNR fields, validator strength, manifest, and audit metadata.
35. `Copy-Item Task\Common\config\*.json Task\Common\stages\stage01_common_definition\snapshot\config\ -Force`
    - Result: refreshed snapshot JSON files after repair.
36. `Copy-Item Task\Common\docs\*.md Task\Common\stages\stage01_common_definition\snapshot\docs\ -Force`
    - Result: refreshed snapshot docs after repair.
37. `Copy-Item Task\Common\scripts\validate_common01_definition.py Task\Common\stages\stage01_common_definition\snapshot\scripts\ -Force`
    - Result: refreshed snapshot validator after repair.
