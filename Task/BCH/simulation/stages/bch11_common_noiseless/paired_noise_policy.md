# Paired noise policy

BCH-11 is noiseless. BCH-12 and later use Common policy version 1. BCH-S200/B200 share noise group
200 and BCH-S300/B300 share noise group 300. A standard Gaussian sample is keyed by global seed,
payload group, SNR index, frame index, policy version, and encoded bit index. Common-prefix positions
therefore share the same standard sample; every case applies its own rate-derived sigma. Longer
codewords continue with new encoded bit indices and never repeat or wrap shorter noise.
