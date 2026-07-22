# BCH Group 4 known issues

- The paired FER=1e-3 coding gain is unavailable because S200 and B300 do not both bracket that
  target within their frozen formal ranges; no extrapolation is used.
- Formal confidence is bounded by 50,000 frames per point and is represented by Wilson 95% intervals.
- Timing tail summaries compare worst per-point quantiles rather than unavailable pooled quantiles.
- Theoretical decoder structure counts are not operation-equivalent.
- Burst errors, interleaving, fading, multipath, frequency offset, Doppler, and soft decoding are
  outside Group 4. Burst-error and interleaving effects are deferred to BCH-17.
