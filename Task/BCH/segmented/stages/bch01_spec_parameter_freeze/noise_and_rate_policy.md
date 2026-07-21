# Noise and rate policy

For every BCH case, `R = original payload length / actual encoded length entering Common BPSK`. Thus S200 is `200/285` and S300 is `300/420`; component `11/15` is never a substitute for a frame rate. `scl::common::computeCodeRate` implements `payloadLength / encodedLength`, so the adapter must set both fields to the frozen whole-frame values. Common `computeAwgnSigma` then uses that `CodeLengths` value. Filler is excluded from the numerator; parity and any future shortening restoration are excluded from the denominator.

The baseline uses no interleaver. Obtain standard Gaussian samples from `NoisePoolReader::readFramePrefix(frameIndex, encodedLength)` and pass the ordered vector to `applyAwgn`.

