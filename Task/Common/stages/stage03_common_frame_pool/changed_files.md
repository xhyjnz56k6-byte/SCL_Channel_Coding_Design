# Changed Files

## Audited Content Commit

`6c304d0ef10fb7620c05ee1ef54b5d4a58f3fe00`

## Added Files

### `Task/Common/include/common/frame_pool.hpp`

- Type: added.
- Purpose: defines deterministic payload generation, packed-bit helpers, manifest structs, manifest loading, and `PackedFramePoolReader`.
- Key functions/classes: `deterministicPayloadBit`, `generatePayloadBits`, `packPayloadBits`, `unpackPayloadBits`, `loadFramePoolManifest`, `PackedFramePoolReader`.
- Algorithm scope: payload frame-pool only; no channel/noise/decoder logic.

### `Task/Common/scripts/generate_common03_frame_pool.py`

- Type: added.
- Purpose: generates 200-bit and 300-bit payload frame pools into shard files and writes `manifest.json` with shard SHA256.
- Key functions: `write_pool`, `generate_payload_bits`, `pack_bits`, `sha256_file`.
- Output location during tests: `Task/Common/build/stage03/`, not submitted.

### `Task/Common/scripts/build_common03.py`

- Type: added.
- Purpose: builds the Common-03 C++ frame-pool test with `g++ -std=c++17 -Wall -Wextra -Werror`.

### `Task/Common/scripts/check_common03.py`

- Type: added.
- Purpose: validates generation reproducibility, different-seed divergence, manifest fields, shard SHA256, Python reader behavior, C++ reader behavior, out-of-range checks, and Git scope.

### `Task/Common/tests/stage03/test_common03_frame_pool.cpp`

- Type: added.
- Purpose: tests C++ packed-bit round trip, deterministic payload generation, manifest parsing, random access, sequential access, and out-of-range reads.

## Audit Closure Files

The audit closure adds this `Task/Common/stages/stage03_common_frame_pool/` directory with plan, changed-file notes, command log, validation report, known issues, manifest, commit metadata, review patch, and snapshot.

The audit closure also updates `Task/Common/scripts/check_common02.py` and its Stage02 snapshot so Common-02 range checks continue to use the explicit Common-02 audited content commit instead of `main...HEAD`. This prevents later Common-03 files from polluting Common-02 validation on the shared batch branch.

## Modified Files Outside Common-03 Scope

Only the Common-02 checker compatibility fix described above.

## Deleted Files

None staged by Common-03.
