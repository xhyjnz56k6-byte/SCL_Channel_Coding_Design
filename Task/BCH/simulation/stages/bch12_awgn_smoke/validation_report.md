# BCH-12 validation report

Functional ranges:

- content: `609f4531a82305c484894599ffbbaa32d8299458...a3674ba7397450b881bb3bcd4a54c7a16a30476a`
- progress-log repair: `a3674ba7397450b881bb3bcd4a54c7a16a30476a...205f82c84811472ace5ca5c45f7ff0d124887b2c`

Release build and BCH-11/BCH-12 CTest passed. BCH-12 processed 20 case-points and 4,000 primary
frames, then repeated all 4,000 frames with identical configuration. All 4,000 standard-noise hashes
were unique within their case-point and all repeat hashes and raw result fields matched. The C++ test
verified shared standard-noise prefixes for S200/B200 and S300/B300. All 20 sigma rows matched the
independent formula within strict tolerance.

At 0 dB the four cases produced 800 aggregate frame errors; at 8 dB they produced 1. All counters
were finite and self-consistent. Progress-enabled, no-progress, dry-run, and invalid-refresh paths
were exercised. The JSONL repair was required because the first publisher found only one of twenty
completion records; after repair the rerun contains exactly 20 COMPLETE point records.

Four matplotlib 3.10.7 PNGs were generated and visually inspected. Each has figure-data CSV and
plot-manifest coverage. PNG magic/header/hash checks passed and non-PNG plot artifact count is zero.

Gate: `PASS_BCH12_AWGN_SMOKE`.
