# Padding and recovery policy

Segmented filler is zero-valued and appended only after the original 200- or 300-bit payload. It reaches the component encoder and channel but is excluded from the rate numerator. The decoder concatenates recovered 11-bit blocks and removes exactly the tail filler count before producing `DecodeResult.payloadBits` of `payloadLength`. `ErrorMetrics` receives only original and recovered payload vectors, so BER, FER, and success rate exclude filler and parity.

