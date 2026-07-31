# stage14_block_continuous_comparison known issues

- No unresolved P0 correctness issue.
- The 50x6, 100x3 and 150x2 BER/FER values are identical at each SNR because they use the same final received sequence and sliding-window boundaries; their slot-driven first-output and P95 delays differ.
- Continuous-progress figures are reconstructed from persisted formal aggregate output-event metrics; no additional Soft formal simulation was run.
- CPU timing is specific to this Release build, host, OS and compiler.
- The channel is symbol-level discrete BPSK-AWGN, without pulse shaping, filtering or sampling-rate effects.
