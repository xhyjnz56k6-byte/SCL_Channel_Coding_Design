# Validation Report

## Environment

- Repository: `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design`
- Branch: `stage02-03-common-foundation`
- Stage: `stage03_common_frame_pool`
- Original functional commit: `6c304d0ef10fb7620c05ee1ef54b5d4a58f3fe00`
- Original audit commit: `5636f802ef2b45d16ff8018dbfe24b171682992f`
- Repair functional commit: `62146787d8ad16e77ad507cd65ba72b06534369e`
- Remote branch: `origin/stage02-03-common-foundation`
- Remote verification status: `VERIFIED`
- Merge status: `NOT_MERGED`

## Executed Commands

```powershell
python Task\Common\scripts\build_common03.py
Task\Common\build\stage03\test_common03_frame_pool.exe Task\Common\build\stage03\pool_a\k200\manifest.json Task\Common\build\stage03\pool_a\k300\manifest.json
python Task\Common\scripts\check_common03.py
python Task\Common\scripts\check_common02.py
git fetch origin
git rev-parse HEAD
git rev-parse origin/stage02-03-common-foundation
git merge-base --is-ancestor 62146787d8ad16e77ad507cd65ba72b06534369e origin/stage02-03-common-foundation
git merge-base --is-ancestor HEAD main
```

## Results

```text
COMMON-03 BUILD: PASS
COMMON-03 TEST PASS
COMMON-03 CHECK: PASS
Gate: PASS_COMMON_FRAME_POOL
COMMON-02 CHECK: PASS
Gate: PASS_COMMON_TYPES_INTERFACES
```

## Common-03 Coverage

- C++ reader verifies shard SHA256 by default.
- Each shard is verified at most once per reader instance.
- Shard damage, truncation, deletion, extra bytes, wrong SHA, and wrong size are rejected.
- Manifest gap, overlap, wrong total, duplicate file name, unsafe file name, invalid SHA, invalid schema, missing fields, wrong bit order, and wrong `overallHash` are rejected.
- K=200 and K=300 regenerate byte-identical shard and manifest files for identical inputs.
- `overallHash` is recomputed and checked by Python and C++.
- Packed-bit byte order is explicitly checked with a known byte fixture.
- Golden vectors for four seed/length/frame cases are frozen.
- C++ and Python agree on sampled frames across shard boundaries.
- Default shard size is 1000; smoke tests explicitly use 10.
- `PackedFramePoolReader` implements `IFramePoolReader`.

## Negative Tests

`negative_test_results.csv` records 26 negative checks. All rows have `verdict=PASS`.

## Audit Checks

- `originalContentRange` matches the original Common-03 functional files.
- `repairContentRange` matches this repair functional commit.
- Stage03 audit files are not counted as functional source.
- Snapshot files match repair functional commit blobs.
- `changes.patch` records both real ranges and does not contain itself.
- `remoteVerificationStatus=VERIFIED`.

## Gate

Gate: PASS_COMMON_FRAME_POOL
