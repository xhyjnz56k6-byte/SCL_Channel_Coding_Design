# BCH-16 validation report

The comparison consumed the committed BCH-15 65-point formal summary and compared only S200/B200
and S300/B300. An independent recomputation verified all twelve target-FER audit rows. Ten targets
were bracketed and matched adjacent-point linear interpolation in log10(FER) to below 1e-12 dB;
S200 at 1e-3 and B300 at 1e-3 were not bracketed, remain blank, and were not extrapolated.

At FER 1e-1 and 1e-2, block-versus-segmented gains are 1.615441 and 2.245331 dB for 200-bit
payloads, and 1.868889 and 2.551997 dB for 300-bit payloads. BCH-B200/B300 also have shorter
encoded lengths and higher rates, while BCH-S200/S300 have materially lower measured software
decode latency and simpler small-table segment structure. The recommendations preserve the
different reported-success semantics and make no operation-equivalence claim for theoretical counts.

Four matplotlib 3.10.7 PNG files were generated with matching figure-data CSVs. Hash, PNG magic,
manifest, non-empty data, and forbidden-extension checks passed. Visual review confirmed readable
200-bit performance and complexity figures; automated checks cover all four. No PDF, SVG, EPS, or
PS artifact exists.

Gate: `PASS_BCH16_SEGMENTED_VS_BLOCK_COMPARISON`.
