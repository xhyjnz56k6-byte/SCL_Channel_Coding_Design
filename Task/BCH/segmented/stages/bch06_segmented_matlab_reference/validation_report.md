# BCH-06 validation report

- MATLAB: R2024b `24.2.0.2712019`, `D:\Apps\Matlab\bin\matlab.exe`.
- Communications Toolbox and `bchenc`, `bchdec`, `bchgenpoly`, `gf`: available; not used as the primary reference.
- Primary independent MATLAB GF(2) long-division reference: PASS.
- CMake build: PASS; CTest: PASS 4/4.
- C++/MATLAB field comparison: PASS; encoder 2048, syndrome 15, no-error decoder 2048, single-error decoder 30720; aggregate mismatch 0.
- MATLAB segmented reference: 208 noiseless frames, 705 single errors, 8 multi-block single-error cases, 12 same-block double-error classifications, 30 filler-boundary cases, and 4 failure-status cases; all required mismatch counters 0.
- Common six binaries: PASS, each exit code 0.
- `Task/Common` diff: empty. Historical BCH-01–05 stage output diff: empty.
- Real patch: base `94ff7eaff3bbe7569f18fa1df35a15367f666b8f` to final functional commit `13df393e2466d61fa73ecad98dc044846d596f87`; isolated worktree reverse-apply check PASS.

Gates: `PASS_BCH06_SEGMENTED_MATLAB_FUNCTIONAL`, `PASS_BCH06_CPP_MATLAB_CROSS_CHECK`, `PASS_BCH06_SEGMENTED_MATLAB_AUDIT`, `PASS_BCH06_SEGMENTED_MATLAB_REFERENCE`.
