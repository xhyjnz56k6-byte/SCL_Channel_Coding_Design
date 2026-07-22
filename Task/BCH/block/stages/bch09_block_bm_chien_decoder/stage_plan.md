# bch09_block_bm_chien_decoder

## Goal
syndrome, Berlekamp-Massey, Chien search, correction and over-capability classification.

## Scope and inputs
BCH-B200/B300, fixed seeds and Common frame pools.

## Non-goals
AWGN, BPSK, interleaving, CC, LDPC and BER/FER.

## Convention
Leftmost bit is highest polynomial degree; systematic `[information][parity]`; shortening removes a known-zero information prefix.

## Tests and Gate
Run `python Task/BCH/block/scripts/run_bch_group3.py --all`. Gate: `PASS_BCH09_BLOCK_ALGEBRAIC_DECODER`. Stop on mismatch, crash, NaN/Inf or nonzero post-syndrome within t.

## Risk
BM iteration trace is not an exact comparison field; final locator and all terminal fields are exact.
