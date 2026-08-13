# Chapter 9 burst-channel definition audit

Source: `Task/Comparison/S7/current/src/s7.cpp` and `Task/Comparison/S7/current/include/s7/s7.hpp`.

## Coding schemes

- BCH fixed scheme: 200 bit payload + 9 bit filler -> 19 x BCH(15,11,1) -> 285 encoded bits. Decoder uses syndrome-table hard-decision BCH(15,11,1) segmented recovery.
- CC fixed scheme: 300 bit payload + 6 zero-tail steps -> 306 trellis steps -> 612 encoded bits. K=7, G1=171(oct), G2=133(oct). Decoder is floating soft terminated full-block Viterbi. No S7 W/S/D sliding-window decoding is used.
- LDPC role: no-interleaving near-rate AWGN baseline only; configuration `LDPC_BG2_K300_N640_DIRECT_LAYERED_NMS_A0P80`.

## Channel model

BPSK mapping:

```text
x_i = +1, bit_i = 0
x_i = -1, bit_i = 1
```

Contiguous burst-error channel:

```text
y_i = h_i x_i + n_i
h_i = -1, s <= i < s + B
h_i = +1, otherwise
n_i = sigma * z_i, z_i ~ N(0, 1)
sigmaSquared = 1 / (2 * 10^(EsN0Db / 10))
```

The burst is applied on the interleaved transmitted sequence. The receiver then demodulates, deinterleaves, and decodes. The interleaver therefore changes the spatial distribution of the contiguous burst as seen by the decoder.

`wrapAround` is false. The channel function rejects wrap-around bursts.

## Burst length

Source rule: `lengthBits = llround(ratio * encodedLength)`.

| Scheme | Encoded length | 2% | 5% | 10% |
|---|---:|---:|---:|---:|
| BCH | 285 | 6 | 14 | 28 |
| CC | 612 | 12 | 31 | 61 |

## Burst start positions

Let `available = encodedLength - B`.

| Position | Start rule |
|---|---|
| HEAD | `s = 0` |
| QUARTER | `s = llround(available / 4)` |
| MIDDLE | `s = llround(available / 2)` |
| THREE_QUARTER | `s = llround(3 * available / 4)` |
| TAIL | `s = available` |
| RANDOM | `s = mix64(2026080427 XOR frameIndex) mod (available + 1)` |

## Formal grid and stop rule

Es/N0 is -5 dB to 10 dB in 0.5 dB steps, 31 points. Burst ratios are 2%, 5% and 10%; positions are HEAD, QUARTER, MIDDLE, THREE_QUARTER, TAIL and RANDOM. Formal stopping is `minFrames=1000`, `targetFrameErrors=200`, `maxFrames=50000`.
