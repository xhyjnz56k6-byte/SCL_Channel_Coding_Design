# Stage Plan

## Stage

`stage03_common_frame_pool`

## Goal

Implement a reproducible, shard-based public payload frame pool foundation for 200-bit and 300-bit payloads.

## Scope

Allowed:

- Deterministic payload bit generation.
- Packed frame-pool shard format.
- `manifest.json` schema and SHA256 verification.
- C++ random/sequential frame-pool reader.
- Python frame-pool generator and checker.
- C++ and Python tests.

Forbidden:

- BPSK, AWGN, sigma, LLR, BER/FER, stop controller, checkpoint/resume I/O.
- BCH, convolutional-code, Viterbi, LDPC, BP, or NMS implementation.
- `Task/BCH/`, `Task/CC/`, `Task/LDPC/`.
- `Task/Common/Plan/` and `Task/Common/build/`.

## Gate

`PASS_COMMON_FRAME_POOL`
