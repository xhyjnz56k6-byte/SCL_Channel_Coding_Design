# BCH-11 frozen specification

## Goal

Prove all four BCH cases traverse the real Common frame pool, encode, BPSK, identity channel,
hard decision, decode, payload recovery, and metric accounting without error.

## Allowed scope

`Task/BCH/simulation/` plus build-time use of existing Common, segmented BCH, and whole-block BCH APIs.

## Forbidden scope

No AWGN implementation, formal infrastructure, CC/LDPC changes, interleaving, or complex channel.

## Contract

- BCH-S200: K=200, N=285, 19 BCH(15,11,1) segments, 9 filler bits.
- BCH-B200: K=200, N=248, shortened BCH(255,207,6), shortening 7.
- BCH-S300: K=300, N=420, 28 BCH(15,11,1) segments, 8 filler bits.
- BCH-B300: K=300, N=390, shortened BCH(511,421,10), shortening 121.
- `reportedSuccess` means all segmented blocks or the whole-block decoder report NO_ERROR/CORRECTED.
- `trueSuccess` is assigned by comparing recovered and original payloads.

## Gate

All 200 real-pool frames and seven deterministic boundary patterns per case must have zero payload
errors, zero hard-decision codeword errors, true/report success rate one, and no miscorrection or
decoder failure. The exact `y=0 -> 0` boundary is tested.
