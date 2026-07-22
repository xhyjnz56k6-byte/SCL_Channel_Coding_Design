# BCH-16 known issues

The paired FER=1e-3 gain is unavailable because BCH-S200 does not bracket 1e-3 and BCH-B300 does
not bracket 1e-3 in their respective frozen formal ranges; no extrapolation is used. Timing P95/P99
entries are worst per-point quantiles, not pooled quantiles. Theoretical structure counts are not
operation-equivalent. Burst errors and interleaving effects are deferred to BCH-17.
