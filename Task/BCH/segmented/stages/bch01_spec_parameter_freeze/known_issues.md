# Known issues and deliberately deferred work

- The BCH(15,11,1) polynomial/bit convention is frozen pending deterministic reference-vector checks.
- Whole-block BCH parameters/shortening are marked `REQUIRES_MATLAB_CONFIRMATION`.
- No BCH algorithm exists in this Stage; all implementation and MATLAB validation belong to later BCH stages.
- The existing Common audit scripts may have assumptions tailored to Common commits; BCH-01 retains reusable Common binary regression without changing those scripts.
- The default CMake generator was unavailable in this environment; MinGW configuration passed. The full source build is TIMEOUT / NOT PROVEN and is not a passing result.
- BCH-01 intentionally contains no BCH algorithm. MATLAB/reference-vector confirmation remains a BCH-02 prerequisite.
