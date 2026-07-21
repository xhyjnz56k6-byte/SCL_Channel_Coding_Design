# Common-04 Random Policy

Noise samples are derived from:

- `masterNoiseSeed`
- `noiseGroupId`
- `frameIndex`
- `symbolIndex`
- `noisePolicyVersion`

The frozen `noiseDomainSeparator = 0x4E4F4953455F3034` is mixed into every noise key. This separates Common-04 noise samples from the Common-03 payload key space.

The policy uses fixed-width unsigned 64-bit arithmetic and the existing SplitMix64 mixer. It does not use system time, `random_device`, process id, thread id, SNR, code type, decoder type or execution order.

Field-change tests use a finite frozen sample set. They verify deterministic differentiation for that set and do not claim all-domain collision freedom.
