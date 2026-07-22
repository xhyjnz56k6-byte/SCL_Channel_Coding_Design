# BCH-15 frozen specification

Read each case's min/max/step directly from the committed BCH-13 recommendation CSV. Construct a
0.2 dB main grid and include the exact recommended maximum as a final 0.1 dB local endpoint when
needed. Use `minFrames=5000`, `targetFrameErrors=200`, `maxFrames=50000`, checkpoint every 2,000
frames, Common paired mother noise, and one clean formal run per point.

Emit the complete raw counters, payload BER/FER, truth/report/miscorrection/failure rates, channel
hard-decision metrics, encode/decode timing and P50/P95/P99/max decode latency, Wilson 95% FER
interval, rule-of-three upper bound for zero errors, stop reason, config hash, and generating Git SHA.

Generate the frozen 15 matplotlib PNGs and one figure-data CSV per PNG. Validate complete unique
points, legal stops, finite/self-consistent fields, progress completion, PNG/data/hash agreement, and
zero non-PNG plot artifacts.

Gate: `PASS_BCH15_AWGN_FORMAL`.
