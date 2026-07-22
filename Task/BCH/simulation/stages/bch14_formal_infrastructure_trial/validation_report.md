# BCH-14 validation report

Functional ranges:

- content: `04b6c4c54273c3294405628cba3e3d5501c6961e...6db579349b9088d4be8cb7dc2d2bdca5e476b0d7`
- progress-state repair: `6db579349b9088d4be8cb7dc2d2bdca5e476b0d7...8d406c50b4e365ff24e0214ae93ee0529c79f09e`

Common CTest registered and passed 7/7 tests. The atomic checkpoint test confirms no temporary file
remains after replacement and compatibility rejection covers schema/experiment/config/frame pool,
length, SNR, Eb/N0, noise policy, seed, shard index, and shard count. BCH-11/BCH-12 CTest passed.

Twelve LOW/MID/HIGH infrastructure points processed 78,650 frames. Every stop reason was
`TARGET_FRAME_ERRORS_REACHED`, never before 5,000 frames. Four 6,000-frame continuous runs matched
their 2,500-frame interruption plus resume runs in every raw counter and all 24,000 frame-noise
hashes. Four continuous runs also matched the raw-count sum of three contiguous 2,000-frame shards.
Rates were recomputed after summing counts.

All 16 checkpoint files contained the required fields, used atomic write/replace, and left no temp
file. Twelve negative executions rejected resume seed/config mismatch, duplicate/missing/overlap
shards, and case/SNR/seed/noise-policy/config-hash mismatch. Multi-shard progress records contain
real shard indices 0/1/2, shard count 3, and real checkpoint counts.

No plot is required by BCH-14; the plot manifest and figure-data audit are explicitly empty and
non-PNG plot artifact count is zero.

Gate: `PASS_BCH14_FORMAL_INFRASTRUCTURE_TRIAL`.
