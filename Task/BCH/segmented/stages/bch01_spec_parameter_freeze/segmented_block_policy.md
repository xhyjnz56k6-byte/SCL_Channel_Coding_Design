# Segmented BCH policy

`BCH-S200`: append 9 zero filler bits, split into 19 eleven-bit blocks, encode each to 15 bits, concatenate to exactly 285 bits. `BCH-S300`: append 8 zero filler bits, split into 28 blocks, encode to exactly 420 bits. No interleaver, puncturing, shortening, CRC, or tail bits are part of this baseline.

The future adapter must construct `scl::common::CodeLengths{payloadLength, payloadLength+fillerBits, encodedLength, encodedLength, fillerBits, 0, 0, 0, 0}`. The BPSK input size must equal `encodedLength` exactly.

