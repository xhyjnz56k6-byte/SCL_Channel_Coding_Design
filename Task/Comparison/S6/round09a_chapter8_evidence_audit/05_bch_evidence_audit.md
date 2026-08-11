# BCH_S6_FORMAL_EVIDENCE_AUDIT

Formal source: `results/bch/formal_v02_20260804`, with 62 formal points, 2046 complexity rows, 62 memory rows, and execution environment JSON.

Comparison boundary: `bch_case_adapter.cpp:13-18` freezes BCH-S200 as payload=200, encodedLength=285, rate=200/285, segmented 19 x BCH(15,11,1), filler=9, syndrome lookup; BCH-B200 as payload=200, encodedLength=248, rate=200/248, whole-block shortened BCH(255,207), shortening=7, t=6, BM+Chien. Encoding dispatch is `bch_case_adapter.cpp:108-111`.

Frozen conclusion: BCH must be written as a complete BCH coding/decoding scheme comparison, not pure decoder-only lookup-vs-BM substitution. Code type, encoded length, rate, correction strength, block organization, and decoder all change.

Lookup counters: S200 maps segmented decoder fields into complexity at `bch_case_adapter.cpp:127-166`: syndrome calculation, bit tests, XOR/shift, lookup, hit/miss, bit flip, post-check. `test_bch_s6_metrics.cpp` confirms syndrome=0 does not perform table lookup.

BM/Chien counters: B200 maps syndrome value/evaluation, BM iterations/discrepancy/locator update/polynomial copy, Chien position/evaluation/root count, bit flip, post-check, and aggregated GF add/multiply/divide/inverse at `bch_case_adapter.cpp:183-203`. GF log/antilog table lookup is not separately exposed.

Memory: `bch_awgn_simulation.cpp:508-523` writes modeled fields: static/object/table/buffer/workspace/total. Method is `EXACT_FROM_TYPE_AND_COUNT`; not full process RSS.

Timing: `bch_awgn_simulation.cpp:337-339` times only `decodeBchFrame(simulationCase, hard)`. Encode, BPSK, AWGN, hard decision, audit, checkpoint, and CSV I/O are outside. `run_bch_formal.ps1` enables 100 timing warmup frames.
