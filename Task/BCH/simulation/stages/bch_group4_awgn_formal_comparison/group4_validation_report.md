# BCH Group 4 validation report

BCH-11 through BCH-16 completed in order on `bch-group4-awgn-formal-comparison`. The six Stage
manifests contain exact functional ranges and every range was checked against its real Git diff.
No CC or LDPC file appears in the Group 4 diff.

- BCH-11: 828 noiseless frames passed for all four unified cases.
- BCH-12: 20 case-points and 4,000 primary frames passed; a second 4,000-frame run matched noise
  hashes and results exactly. Four matplotlib PNGs passed their audits.
- BCH-13: 84 case-points and 168,000 frames passed; four formal grids were frozen. Six PNGs passed.
- BCH-14: 12 trial points and 78,650 frames passed; four continuous/resume comparisons, four
  three-shard raw-count merges, 16 checkpoint field/atomic checks, and 12 negative rejections passed.
- BCH-15: 65 formal points and 1,134,718 frames passed. Stop distribution was 52 target-frame-error
  stops and 13 maximum-frame stops. Fifteen matplotlib PNGs passed.
- BCH-16: twelve target interpolation audits contained ten bracketed interpolations and two explicit
  no-extrapolation results. Six coding-gain rows, four comparison rows, and four PNGs passed.

Fresh historical regression passed Common CTest 7/7, segmented BCH CTest 4/4, whole-block BCH
CTest 1/1, and the combined Group 4 CTest 7/7. MATLAB R2024b cross-checks passed the BCH-06 single
block and segmented references and BCH-07--10 parameter, toolbox, GF-detail (3,834 rows), Common
frame-pool, decode-detail, illegal-input (10 rows), and toolbox-codec (5,104 single-error cases)
references.

The ordered runner's BCH-11 entry was executed after repair and passed its rebuild plus dedicated
CTest, so `--all` now begins at BCH-11 before continuing through BCH-12--16.

Across BCH-12, BCH-13, BCH-15, and BCH-16, 29 committed plots are PNG files generated only by
matplotlib 3.10.7; the non-PNG plot artifact count is zero. Progress can be enabled/disabled, uses
bounded refresh, records JSONL for simulation stages, includes checkpoint/shard state, and provides
two explicit processing steps in BCH-16.

Group Gate: `PASS_BCH_GROUP4_AWGN_FORMAL_COMPARISON`.
