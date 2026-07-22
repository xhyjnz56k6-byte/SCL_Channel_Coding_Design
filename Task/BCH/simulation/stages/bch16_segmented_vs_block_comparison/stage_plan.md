# BCH-16 specification freeze

Goal: compare only BCH-S200 with BCH-B200 and BCH-S300 with BCH-B300 using committed BCH-15
formal AWGN data. Produce target-FER interpolation audits, coding gains, theoretical structure
counts, latency summaries, recommendations, and four matplotlib PNG files.

Non-goals: no new channel simulation, no extrapolation, no interleaving, burst-error, fading, soft
decoding, CC, or LDPC work. Interpolation is linear only between bracketing adjacent formal points
in log10(FER) versus Eb/N0.

Gate: `PASS_BCH16_SEGMENTED_VS_BLOCK_COMPARISON`.
