# BCH-16 recommendations

For 200-bit payloads, BCH-B200 uses 248 transmitted bits at rate 0.8065 versus BCH-S200's 285 bits at rate 0.7018. It needs 1.615 dB less Eb/N0 at FER=1e-1 and 2.245 dB less at FER=1e-2. BCH-S200 did not bracket 1e-3, so no paired 1e-3 gain is claimed. BCH-S200's frame-weighted average software decode time is 14.832 us versus 47.711 us for BCH-B200. Choose BCH-B200 for AWGN BER/FER, rate, and fewer transmitted/stored codeword bits; choose BCH-S200 for tiny fixed lookup tables, independent-block parallel hardware, and lower measured software latency.

For 300-bit payloads, BCH-B300 uses 390 transmitted bits at rate 0.7692 versus BCH-S300's 420 bits at rate 0.7143. It needs 1.869 dB less Eb/N0 at FER=1e-1 and 2.552 dB less at FER=1e-2. BCH-B300 did not bracket 1e-3, so no paired 1e-3 gain is claimed. BCH-S300's frame-weighted average software decode time is 21.967 us versus 127.740 us for BCH-B300. Choose BCH-B300 for AWGN BER/FER, rate, and fewer transmitted/stored codeword bits; choose BCH-S300 for regular segment parallelism, small lookup tables, and lower measured software latency.

True success is exactly one minus payload FER. Reported-success semantics differ: segmented miscorrections remain reported successes, while whole-block bounded-distance failures are explicit decoder failures. Therefore true success, reported success, miscorrection, and decoder failure must be interpreted together. Tail timing uses the worst per-point P95/P99/max rather than claiming an unavailable pooled quantile. Structural counts are not operation-equivalent: segmented lookup loops favor simple parallel control, whereas BM/Chien decoding uses more GF arithmetic but avoids many independent segment decisions.

突发错误和交织影响留待 BCH-17。
