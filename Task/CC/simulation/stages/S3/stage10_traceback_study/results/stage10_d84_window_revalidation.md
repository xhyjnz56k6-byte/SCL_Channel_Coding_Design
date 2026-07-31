# D84 true-window revalidation

All four modes use the same payload, encoded stream, puncturing, Gaussian mother noise, SNR, frame indices and stop rule at each rate/FER-level scenario.

| rateCase | mode | worstRelativeFerIncreaseVsBlock | maxMismatchFramesVsBlock | meanDecodeTimeUs | maxTotalMemoryBytes | meanTracebackOperationsPerFrame |
| --- | --- | --- | --- | --- | --- | --- |
| R12 | CONTINUOUS_TRUNCATED_D84 | 0.003378378378378383 | 3 | 616.8626220869901 | 17664 | 18732.0 |
| R12 | TRUE_SLIDING_WINDOW_D84 | 0.0 | 1 | 1311.1192081705678 | 26112 | 978.0 |
| R12 | TRUE_SLIDING_WINDOW_BALANCED | 0.0 | 2 | 1294.9004372393856 | 26112 | 866.0 |
| R23 | CONTINUOUS_TRUNCATED_D84 | 0.0686274509803926 | 65 | 578.2089959674473 | 17664 | 18732.0 |
| R23 | TRUE_SLIDING_WINDOW_D84 | 0.014999999999999479 | 21 | 1260.3984514526016 | 26112 | 978.0 |
| R23 | TRUE_SLIDING_WINDOW_BALANCED | 0.006535947712418672 | 10 | 1243.7481662230682 | 26112 | 1090.0 |
| R34 | CONTINUOUS_TRUNCATED_D84 | 0.1739130434782611 | 123 | 528.1231370963379 | 17664 | 18732.0 |
| R34 | TRUE_SLIDING_WINDOW_D84 | 0.07023411371237505 | 61 | 1243.5504751140006 | 26112 | 978.0 |
| R34 | TRUE_SLIDING_WINDOW_BALANCED | 0.0 | 5 | 1216.4079733263688 | 32256 | 1062.0 |

D84 is revoked as a final true-window recommendation because at least one rate exceeds the 5% FER gate.
