# Chapter 9 evidence audit report

Gate: PASS_ROUND10_A_S7_CHAPTER9_FORMAL_EVIDENCE_AUDIT

Branch: S8-PaperDocu

HEAD: 76dc4b5575399559e7e25409fedc199e29090226

## Figure counts

- Stage15 total plots: 51 (actual audited directories: 51)
- BCH plots: 29
- CC plots: 22
- A/B/C importance counts: A=29, B=22, C=0

## LDPC baseline

- configurationId: LDPC_BG2_K300_N640_DIRECT_LAYERED_NMS_A0P80
- payloadBits: 300
- transmittedBits: 640
- actualRate: 0.46875
- CC actualRate: 0.49019607843137253
- decoder: DIRECT_LAYERED_NMS, alpha=0.8, maxIterations=32
- interleaver: NONE
- channel: NO_BURST_AWGN
- role: no-interleaving near-rate AWGN reference only

## Fixed schemes

- BCH fixed scheme: 200 bit payload + 9 bit filler -> 19 x BCH(15,11,1) -> 285 encoded bits.
- CC fixed scheme: 300 bit payload + 6 zero-tail steps -> 306 trellis steps -> 612 encoded bits; K=7, G1=171(oct), G2=133(oct); terminated full-block floating soft Viterbi.

## Interleaver summary

- BCH NONE: identity permutation, bufferBits=0.
- BCH_CODEBLOCK: D in {4,8,16,19}; D=19 forms a 19 x 15 BCH subblock-structured interleaver, column-read within BCH codeblock organization, spanBits=285, bufferBits=285.
- BCH ROW_COLUMN: row-write/column-read over the full 285 bit frame; R=15 in formal config, spanBits=285, bufferBits=285.
- BCH GLOBAL_PSEUDORANDOM: deterministic full-frame 285 bit permutation with fixed seed, spanBits=285, bufferBits=285.
- CC NONE: identity trellis-step order, preserves mother-code output pairs, bufferBits=0.
- CC SHORT_DEPTH_BLOCK: D in {4,8,16}, window=8*D trellis steps, preserves each mother-code output pair.
- CC PSEUDORANDOM: span in {32,64,128} trellis steps, deterministic shuffle inside local windows, not a full-frame 306 step shuffle.
- D8 span/buffer: 64 trellis steps / 128 coded bits.
- D16 span/buffer: 128 trellis steps / 256 coded bits.
- pseudo128 span/buffer: 128 trellis steps / 256 coded bits.

## Fairness and timing

- Formal fairness audit rows: 1116
- Fairness failures: 0
- Timing path: interleave/deinterleave/decode steady_clock CPU function timing only; bufferBits is structural coded-bit buffering depth and is not converted to physical delay.

## Blocking issues

None blocking for Chapter 9 evidence use when LDPC and wording boundaries are respected.

## Generated files

See `readme.txt` in this directory for the complete file list.

## Git

- commit: NO
- push: NO
- stage: NO
- merge main: NO
