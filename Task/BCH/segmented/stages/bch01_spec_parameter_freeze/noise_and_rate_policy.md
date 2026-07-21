# Noise and rate policy

For every BCH case, `R = original payload length / actual encoded length entering Common BPSK`. The four frozen rates are S200 `200/285`, S300 `300/420`, B200 `200/248`, and B300 `300/390`; component `11/15` is never a substitute for a frame rate. `scl::common::computeCodeRate` implements `payloadLength / encodedLength`, so the adapter must set both fields to the frozen whole-frame values. Common `computeAwgnSigma` then uses that `CodeLengths` value.

- Filler is excluded from the numerator.
- Every coded bit actually passed to Common BPSK and the channel is included in the denominator: systematic bits, parity bits, and transmitted bits created by encoding filler.
- Only virtual mother-code positions that are not transmitted and are restored solely during shortened decoding are excluded from the denominator.

The baseline uses no interleaver. Obtain standard Gaussian samples from `NoisePoolReader::readFramePrefix(frameIndex, encodedLength)` and pass the ordered vector to `applyAwgn`.
