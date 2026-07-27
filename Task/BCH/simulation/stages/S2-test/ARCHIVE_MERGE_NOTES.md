# BCH S2 prototype archive merge notes

- Source branch A: `bch-s2-burst-redesign-and-plot-quality` at `df5aac541604fbdbb029de310abb7ea8f380f4c2`.
- Source branch B: `bch-s2-semi-finished-archive-reorganization` at `9045a1da5da34cbb529a018db031ec5965757ad9`.
- Common merge base: `069373b02401ad0acc10d96eb4e63bad8763c64c`.
- Merge order: branch A, then branch B.

## Conflict record

One conflict occurred in `Task/BCH/simulation/current/CMakeLists.txt`.
The archive retains the S2-test layout for the moved multipath/MMSE module,
and retains the burst/redesign impairment, burst, interleaver, runner, and
test targets. The resolved CMake graph uses `bch_s2_multipath` once and links
the retained impairment/burst targets through `bch_s2_impairment`; it does not
compile duplicate multipath/MMSE implementations.

## Archive purpose

This branch preserves prototype history, original/corrected/redesign material,
and historical audit evidence. It is not a formal-experiment branch and must
not be merged directly into `main`.
