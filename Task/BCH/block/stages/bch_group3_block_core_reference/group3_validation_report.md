# Group 3 validation

One-click build and CTest passed. MATLAB self-reference: 9,416 exact detail rows; GF: 3,834 rows; illegal input: 10 rows; real frame-pool encoder: 200 rows. The 1,248 over-capability cases cover payload-only, parity-only, payload/parity mixed, adjacent, first/last boundary, widely-separated and deterministic-random patterns. Communications Toolbox 24.2 executed bchgenpoly, bchenc and bchdec; 5,104 all-position single-error decodes passed. BCH-06 regression passed 4/4 CTest and both MATLAB checkers. Total mismatch: 0. The remote branch contains the audited functional commit.

BM per-iteration trace is not claimed; final locator is exact.

Gate: `PASS_BCH_GROUP3_BLOCK_CORE_REFERENCE`.
