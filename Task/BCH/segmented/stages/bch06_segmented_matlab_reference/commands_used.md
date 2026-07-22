# BCH-06 commands

- `matlab -batch "disp(version); ... exist('bchenc','file')"`
- `cmake -G "MinGW Makefiles" -S Task/BCH/segmented/current -B Task/BCH/segmented/build/bch06_segmented_matlab_reference/cmake -DCMAKE_BUILD_TYPE=Release`
- `cmake --build ...`
- `ctest --test-dir ... --output-on-failure`
- `export_bch06_cpp_reference <build>/cpp_outputs`
- `matlab -batch "addpath(...); run_bch06_segmented_matlab_reference(...);"`
- `python Task/BCH/segmented/scripts/check_bch06_segmented_matlab_reference.py ...`
- `python Task/BCH/segmented/scripts/generate_bch06_audit.py`
- Common stage04 six regression binaries
- `git diff --check`; isolated `git worktree add --detach ... 13df393` and `git apply --check --reverse changes.patch`
