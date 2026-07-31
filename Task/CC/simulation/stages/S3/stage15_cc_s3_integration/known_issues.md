# stage15_cc_s3_integration known issues

- No unresolved P0 correctness issue.
- Stage13 actual controls are W study S16/D70, S study W160/D70 and D study W160/S16. D126 was not run because of the stated compute budget, so no report claims D126 coverage.
- FER=0.1 SNR values use adjacent real points and log-FER interpolation only when the target is bracketed.
- Same-SNR rate comparisons share channel conditions but not redundancy or net throughput.
- CPU timing is specific to this Release build, host, OS and compiler.
