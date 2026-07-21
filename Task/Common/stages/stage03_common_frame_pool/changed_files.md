# Changed Files

## Original Common-03 Functional Commit

`6c304d0ef10fb7620c05ee1ef54b5d4a58f3fe00`

## Repair Functional Commit

`47710d2119041139bdaef577815023473c525730`

## Functional Changes

### `Task/Common/include/common/sha256.hpp`

- Type: added.
- Purpose: pure C++17 SHA256 implementation.
- Key functions/classes: `Sha256`, `sha256Hex`, `sha256FileHex`.

### `Task/Common/include/common/frame_pool.hpp`

- Type: modified.
- Purpose: hardens manifest validation, payload policy versioning, bit format definition, shard SHA256 checks, `overallHash`, and reader inheritance.
- Key functions/classes: `validateFramePoolManifest`, `computeFramePoolOverallHash`, `PackedFramePoolReader`.

### `Task/Common/scripts/generate_common03_frame_pool.py`

- Type: modified.
- Purpose: deterministic manifest v2 generation, `overallHash`, `--overwrite`, default `--shard-size 1000`, and payload policy v2 derivation.

### `Task/Common/scripts/check_common03.py`

- Type: modified.
- Purpose: full Common-03 Gate, including reproducibility, manifest byte equality, shard SHA256, `overallHash`, golden vectors, C++/Python comparison, negative mutation tests, snapshot checks, and dual-range audit checks.

### `Task/Common/tests/stage03/test_common03_frame_pool.cpp`

- Type: modified.
- Purpose: tests `IFramePoolReader` inheritance, SHA256, explicit bit packing, golden vectors, K=200/K=300 reads, cross-shard reads, damaged shard rejection, manifest gap/overlap/count/sha/overallHash failures, truncation, and unused tail bits.

## Audit Closure Files

Updated or added under `Task/Common/stages/stage03_common_frame_pool/`:

- `stage_plan.md`
- `changed_files.md`
- `validation_report.md`
- `manifest.json`
- `changes.patch`
- `frozen_config.csv`
- `commands_used.md`
- `git_commit.txt`
- `known_issues.md`
- `snapshot/`
- `frame_pool_format.md`
- `fixture_hashes.csv`
- `cpp_python_comparison.csv`
- `negative_test_results.csv`
- `golden_vectors.csv`

## Forbidden Areas

No Common-03 staged change includes `Task/Common/Plan/`, `Task/Common/build/`, `Task/BCH/`, `Task/CC/`, or `Task/LDPC/`.
