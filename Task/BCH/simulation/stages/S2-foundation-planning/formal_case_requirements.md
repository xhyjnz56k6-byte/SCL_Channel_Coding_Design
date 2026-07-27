# Formal S2 case requirements

This branch defines interfaces only; it does not freeze a framing policy or
produce formal performance results.

| Payload | BCH(15,11) | BCH(255,207) | BCH(511,421) | BCH(511,385) |
|---|---|---|---|---|
| 200 bit | segmented framing required | single shortened block can contain 200 | single shortened block can contain 200 | single shortened block can contain 200 |
| 300 bit | segmented framing required | REQUIRES_FORMAL_FRAMING_POLICY | single shortened block can contain 300 | single shortened block can contain 300 |

For BCH(255,207) with a 300-bit payload, the framing/segmentation policy must
be explicitly approved before formal runs. This branch does not infer one.
All four schemes require identical channel, seed, stopping, and metric
contracts before a comparison can be claimed.
