# BCH-15 validation report

Functional ranges:

- formal driver and plots: `8e822a1b90e3816d4a3ef0d47c4524ecc07a1246...ad57f9cac5946e842160d085e8ddbc19acafbf15`
- artifact publisher: `ad57f9cac5946e842160d085e8ddbc19acafbf15...bce2c240c062359651ffdb77d090adb646eeff5d`

The formal run used the exact BCH-13 frozen recommendations: BCH-S200 4.5--8.5 dB at 0.2 dB,
BCH-B200 3.5--5.9 dB at 0.2 dB plus 6.0 dB, BCH-S300 5.0--9.0 dB at 0.2 dB,
and BCH-B300 4.0--5.4 dB at 0.2 dB plus 5.5 dB. All 65 planned case-points are present
exactly once and processed 1,134,718 frames. Fifty-two points reached 200 frame errors after the
5,000-frame minimum; thirteen reached the 50,000-frame maximum.

An independent Python audit recomputed BER, FER, true/reported success identities, miscorrection and
decoder-failure bounds, Wilson 95% intervals, stop rules, and timing quantile order. It also matched
the frozen grid, 65 final progress states, and 65 checkpoint summaries. No mismatch, NaN, Inf,
illegal stop reason, missing point, or duplicate point was found.

The plot audit verified 15 matplotlib 3.10.7 PNG files, their magic bytes, SHA-256 values, source
figure data, and manifest entries. No PDF, SVG, EPS, or PS artifact exists. Visual inspection covered
the 200-bit and 300-bit FER curves and confirmed readable titles, axes, legends, log scaling, and
complete series.

Gate: `PASS_BCH15_AWGN_FORMAL`.
