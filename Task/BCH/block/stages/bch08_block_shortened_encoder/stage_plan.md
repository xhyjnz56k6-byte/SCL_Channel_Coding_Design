# bch08_block_shortened_encoder

## Goal
systematic mother encoding, shortening, divisibility and real Common frame pools.

## Scope and inputs
BCH-B200/B300, fixed seeds and Common frame pools.

## Non-goals
AWGN, BPSK, interleaving, CC, LDPC and BER/FER.

## Convention
Leftmost bit is highest polynomial degree; systematic `[information][parity]`; shortening removes a known-zero information prefix.

## Tests and Gate
Run `python Task/BCH/block/scripts/run_bch_group3.py --all`. Gate: `PASS_BCH08_BLOCK_SHORTENED_ENCODER`. Stop on mismatch, crash, NaN/Inf or nonzero post-syndrome within t.

## Risk
BM iteration trace is not an exact comparison field; final locator and all terminal fields are exact.
