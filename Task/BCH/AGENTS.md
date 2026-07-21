# BCH local rules

- Keep segmented and block BCH work in separate subdirectories.
- Do not modify `Task/Common`, `Task/CC`, or `Task/LDPC` for a BCH stage.
- BCH-01 is documentation-only: no encoder, decoder, GF arithmetic, AWGN runner, or MATLAB implementation is permitted.
- All BCH code-rate reporting uses the original payload length divided by the actual encoded length passed to Common BPSK.
