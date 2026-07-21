# BCH(15,11,1) bit and polynomial convention

The segmented component candidate is `n=15`, `k=11`, `t=1`, with `g(x)=x^4+x+1` and systematic layout `[11 information bits][4 parity bits]`. `message[0]` maps to `x^10`; `message[10]` maps to `x^0`; `codeword[0]` maps to `x^14`; `codeword[14]` maps to `x^0`. Filler is appended to the complete payload before 11-bit segmentation and removed after decoding back to `payloadLength`.

These bit/polynomial choices are `FROZEN_PENDING_REFERENCE_VECTOR_CHECK`. BCH-02 must not treat them as MATLAB-validated until deterministic reference vectors have been checked.
