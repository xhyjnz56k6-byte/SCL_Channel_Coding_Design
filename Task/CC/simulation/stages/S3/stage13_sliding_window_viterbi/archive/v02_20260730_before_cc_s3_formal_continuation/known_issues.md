# stage13_sliding_window_viterbi known issues

- No unresolved P0 correctness issue.
- CPU timing is specific to the recorded Release build, host, operating system and compiler.
- The channel is symbol-level discrete BPSK-AWGN; it does not model sampling rate, pulse shaping, matched filtering or noise bandwidth.
- Formal zero-error BER/FER values remain zero; confidence upper bounds are stored and used only for display.
