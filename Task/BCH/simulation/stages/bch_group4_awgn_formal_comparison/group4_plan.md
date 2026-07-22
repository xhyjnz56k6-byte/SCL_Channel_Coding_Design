# BCH Group 4 frozen plan

## Objective

Complete BCH-11 through BCH-16 on branch `bch-group4-awgn-formal-comparison`, ending at
`PASS_BCH_GROUP4_AWGN_FORMAL_COMPARISON`.

## Functional scope

- Add a unified simulation adapter for BCH-S200, BCH-B200, BCH-S300, and BCH-B300.
- Reuse the Common frame pool, deterministic Gaussian noise, BPSK, AWGN, hard decision,
  metrics, stop control, checkpoint primitives, hashing, CSV conventions, and matplotlib style.
- Run noiseless, smoke, prescan, infrastructure trial, formal AWGN, and segmented-versus-block comparison in order.
- Produce only PNG plots with Python matplotlib.

## Non-goals

- No interleaving, burst-error channel, fading, multipath, frequency offset, Doppler, or soft BCH decoding.
- No modification of CC or LDPC implementation.
- No automatic merge to `main`.

## Frozen interfaces and data rules

- Rate is `payloadLength / encodedLength` using the transmitted BCH codeword length.
- BER and FER compare recovered payload with original payload only.
- Paired standard Gaussian samples share `(payloadGroup, snrIndex, frameIndex, encodedBitIndex)`;
  each case then applies its own rate-derived sigma.
- Stages stop immediately when their Gate fails. BCH-15 reads the SNR grid frozen by BCH-13.
- Result plots are individual figures, Agg backend, explicit PNG save, and closed after saving.

## Stage order and Gates

1. BCH-11: `PASS_BCH11_COMMON_INTEGRATION_NOISELESS`
2. BCH-12: `PASS_BCH12_AWGN_SMOKE`
3. BCH-13: `PASS_BCH13_AWGN_PRESCAN`
4. BCH-14: `PASS_BCH14_FORMAL_INFRASTRUCTURE_TRIAL`
5. BCH-15: `PASS_BCH15_AWGN_FORMAL`
6. BCH-16: `PASS_BCH16_SEGMENTED_VS_BLOCK_COMPARISON`

The user request explicitly authorizes continuous execution, normal commits, and a normal push,
so no additional confirmation pause is required between these frozen stages.
