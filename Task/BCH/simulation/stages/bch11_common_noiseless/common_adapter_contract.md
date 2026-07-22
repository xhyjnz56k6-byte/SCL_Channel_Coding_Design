# Common adapter contract

The simulation layer accepts one frozen `BchSimulationCase` and one payload bit vector. It hides
segmented block count/filler handling and whole-block shortening/t parameters from callers. The
encoder returns exactly the transmitted codeword. The decoder returns recovered payload, reported
status, block counters, whole-block status, and diagnostics. The runner assigns truth-derived
`trueSuccess` and `miscorrected` by comparing with the original payload.

Segmented success requires every BCH(15,11,1) block to report `NO_ERROR` or
`CORRECTED_SINGLE_ERROR`. Whole-block success requires `NO_ERROR` or `CORRECTED` from the existing
BM+Chien decoder.
