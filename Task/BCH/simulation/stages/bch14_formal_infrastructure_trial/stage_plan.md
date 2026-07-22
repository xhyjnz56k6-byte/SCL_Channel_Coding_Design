# BCH-14 frozen specification

Use LOW/MID/HIGH measured points from BCH-13 for 12 infrastructure-trial case-points. Apply
`minFrames=5000`, `targetFrameErrors=100`, `maxFrames=20000`. Extend the existing Common checkpoint
record backward-compatibly, write atomically through temp/flush/replace, protect all simulation
identity and stop fields with a canonical config hash, and preserve BCH raw counters.

For each case, compare a fixed continuous run with partial+resume to the same frame count. Compare a
fixed continuous run with the sum of three contiguous shards. Reject duplicate, overlap, missing
range, config/case/SNR/seed/noise-policy mismatches. Rates are recomputed only after raw-count merge.

Gate: `PASS_BCH14_FORMAL_INFRASTRUCTURE_TRIAL`.
