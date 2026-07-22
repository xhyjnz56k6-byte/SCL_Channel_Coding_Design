# BCH-05 segmented adapter and recovery stage plan

## Goal

Implement the BCH(15,11,1) segmented adapter for the frozen 200 bit and 300 bit payload cases. The stage converts Common payload bits into 11 bit BCH message blocks, appends tail filler zeros, encodes each block with the BCH-02 encoder, concatenates 15 bit codewords, decodes hard bits with the BCH-04 lookup decoder, removes filler, and recovers the original payload.

## Non-goals

This stage does not implement BPSK, AWGN, noise, BER/FER runners, MATLAB validation, whole-frame BCH, BM, Chien search, interleaving, or BCH-06 work.

## Formal API

The adapter API is in `Task/BCH/segmented/current/include/bch_segmented/bch15_segmented_adapter.hpp`.

- `Bch15SegmentedCase`: explicit case selector, `S200` or `S300`.
- `Bch15SegmentedConfig`: frozen case profile with payload length, block size, block count, filler bits, encoded length, and code rate inputs.
- `Bch15SegmentedEncodeResult`: frozen config, Common `CodeLengths`, padded message bits, and encoded bits.
- `Bch15SegmentedDecodeResult`: frozen config, recovered payload, recovered padded message, per-block BCH-04 detail, and BCH-specific frame detail.
- `encodeBch15Segmented(caseId, payloadBits)`: validates explicit case and payload length.
- `decodeBch15Segmented(caseId, receivedBits, table)`: validates explicit case and encoded length, and reuses one caller-built `const SyndromeTable&`.
- `auditBch15SegmentedRecovery(originalPayload, result)`: test/audit helper that compares decoder output to truth without polluting Common metrics.

## Frozen cases

| case | payloadLength | blockPayloadLength | blockCount | fillerBits | encodedBlockLength | encodedLength | codeRate | last block |
|---|---:|---:|---:|---:|---:|---:|---|---|
| BCH-S200 | 200 | 11 | 19 | 9 | 15 | 285 | 200/285 | 2 payload + 9 filler |
| BCH-S300 | 300 | 11 | 28 | 8 | 15 | 420 | 300/420 | 3 payload + 8 filler |

`computeCodeRate` from Common is called and checked for both cases.

## Index mapping

- `payload[i]` maps to `paddedMessage[i]` for `0 <= i < payloadLength`.
- Tail filler zeros occupy `paddedMessage[payloadLength, payloadLength + fillerBits)`.
- Block `b` uses message indices `[11*b, 11*b+11)` and encoded-frame indices `[15*b, 15*b+15)`.
- BCH systematic bits keep the block-local order: local codeword positions `0..10` are message bits, `11..14` are parity bits.
- BCH-S200 block 18 has local message positions `0..1` from `payload[198..199]`, and `2..10` filler.
- BCH-S300 block 27 has local message positions `0..2` from `payload[297..299]`, and `3..10` filler.
- Recovery concatenates all BCH-04 decoded 11 bit messages and returns only `[0, payloadLength)`.

If BCH-04 reports `POST_CHECK_FAILED` or `UNRECOGNIZED_SYNDROME`, BCH-05 still concatenates the returned BCH-04 information bits and preserves the failure status in block detail. Reported decoder success is not treated as truth recovery.

## Test matrix

| class | coverage | required truth check |
|---|---|---|
| No error | zero, one, alternating, last-bit-one synthetic frames for S200/S300; Common pool frameIndex 0..99 for both pools | payload mismatch = 0 and all blocks NO_ERROR |
| Single block single error | S200 first 9 blocks x 15 positions; S300 first 8 blocks x 15 positions | corrected block, local/global position, corrected codeword, recovered payload |
| Multiple blocks, one error each | first+last, adjacent blocks, three spread blocks, and every block one error | recovered frame payload and corrected block count |
| Same block double error | two payload bits, payload+parity, two parity bits, payload+filler, two filler bits, filler+parity | status, codeword truth, block message truth, frame payload truth |
| Filler boundary | every local position of the last block for both cases | payload/filler/parity classification and recovered payload |
| Negative inputs | wrong payload length, non-bit payload, wrong encoded length, non-bit received bits | explicit rejection |

Error injection exists only in tests.

## Common frame pools

- S200 manifest: `Task/Common/build/stage04/real_pool_runs/smoke/frames/k200/manifest.json`
- S200 pool ID: `payload_k200_seed2026072001_policy1_frames100`
- S300 manifest: `Task/Common/build/stage04/real_pool_runs/smoke/frames/k300/manifest.json`
- S300 pool ID: `payload_k300_seed2026072001_policy1_frames100`
- Frame range: `frameIndex=0..99`.

The pool manifests are read-only inputs and are not copied or modified.

## Output isolation

Normal CTest output is written only under:

- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch02_encoder`
- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch03_syndrome_table`
- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch04_lookup_decoder`
- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch05_segmented_adapter`

Historical `Task/BCH/segmented/stages/bch02_*`, `bch03_*`, and `bch04_*` directories are frozen evidence and must not be runtime output targets.

## Gate

`PASS_BCH05_SEGMENTED_ADAPTER_RECOVERY` requires:

- S200/S300 frozen parameters match the stage profile.
- encoded length, filler mapping, and block order are correct.
- no-noise payload mismatch is zero for synthetic frames and Common pool 100+100 frames.
- all tested encoded blocks are legal BCH(15,11,1) codewords.
- single block single errors recover and report the correct position.
- multiple blocks with one error each recover the frame payload.
- same block double errors are classified with decoder status and truth separated.
- Common six binary regressions pass.
- `Task/Common` is not modified.
- no BCH-06, AWGN, BPSK, BM, Chien, interleaver, or BER/FER runner content is introduced.
