# Stage Plan

## Stage

`stage03_common_frame_pool`

## Goal

Finalize a reproducible, integrity-checked, shard-based public payload frame pool for 200-bit and 300-bit payloads.

## Functional Scope

- Deterministic payload generation with `payloadPolicyVersion = 1`.
- SplitMix64 payload derivation version `splitmix64_payload_v2`.
- Packed payload bytes with `bitOrderWithinByte = lsb_first`.
- Default shard size of 1000 frames.
- Manifest v2 with deterministic bytes, shard SHA256, and `overallHash`.
- C++ `PackedFramePoolReader final : public IFramePoolReader`.
- Pure C++17 SHA256 implementation.
- C++ and Python validation, including real damaged-input negative tests.

## Explicitly Excluded

BPSK, AWGN, Gaussian noise, sigma, LLR, BER/FER, Wilson intervals, stop controller, checkpoint/resume, BCH, convolutional-code, Viterbi, LDPC, BP/NMS, and interleaving.

## Gate

`PASS_COMMON_FRAME_POOL`
