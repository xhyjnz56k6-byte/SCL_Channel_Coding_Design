# Common-04 Simulation Formula

Code rate reuses the frozen Common function:

```text
computeCodeRate() = payloadLength / encodedLength
```

Common-04 tests include:

```text
R = 200 / 248
R = 300 / 390
```

BPSK mapping:

```text
bit 0 -> +1
bit 1 -> -1
```

AWGN:

```text
EbN0Linear = 10^(EbN0_dB / 10)
sigma = sqrt(1 / (2 * R * EbN0Linear))
received = symbol + sigma * standardGaussianNoise
```

LLR:

```text
LLR = 2 * received / sigma^2
positive LLR means bit 0
```

Hard decision:

```text
received >= 0 -> bit 0
received < 0 -> bit 1
```

Monte Carlo trend checks are sanity checks. Higher SNR BER should be grossly non-increasing for frozen smoke/prescan cases, but short samples are not required to be strictly pointwise monotonic.
