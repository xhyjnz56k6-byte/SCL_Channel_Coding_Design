# BCH-13 frozen specification

Run BCH-S200, BCH-B200, BCH-S300, and BCH-B300 from 0.0 through 10.0 dB in 0.5 dB steps,
2,000 fixed frames per point, for 84 case-points and 168,000 frames. Reuse the BCH-12 signal chain,
noise policy, progress reporter, accounting, and timing. Identify measured waterfall LOW/MID/HIGH
points and freeze a 0.2 dB formal recommendation for each case without extrapolating FER targets.

Generate the six frozen BCH-13 matplotlib PNGs, figure-data audit, status distribution, timing summary,
and recommendation CSV. No early stop, checkpoint/resume, shard merge, or formal run is in scope.

Gate: `PASS_BCH13_AWGN_PRESCAN`.
