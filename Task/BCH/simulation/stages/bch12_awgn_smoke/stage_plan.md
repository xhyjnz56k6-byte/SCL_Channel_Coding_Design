# BCH-12 frozen specification

## Goal

Run the four BCH cases over the Common BPSK/AWGN/hard-decision chain at 0, 2, 4, 6, and 8 dB,
using 200 fixed frames per point (4,000 total frames), paired reproducible standard Gaussian noise,
rate-derived sigma, detailed optional progress, and matplotlib-only PNG plots.

## Non-goals

No early stop, checkpoint/resume, shard merge, formal range selection, interleaving, burst channel,
complex channel, or soft decoding.

## Gate

Noise is unique across frames and reproducible across identical reruns. Cases of equal payload length
share standard mother-noise prefixes but apply different sigma. Counters are finite and self-consistent,
0 dB aggregate performance is worse than 8 dB, progress can be shown or disabled, all expected PNGs
and figure-data records exist, and no PDF/SVG/EPS/PS artifact is generated.
