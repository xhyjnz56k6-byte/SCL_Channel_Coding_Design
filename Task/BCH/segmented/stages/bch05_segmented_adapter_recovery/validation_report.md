# BCH-05 validation report

## Git and scope

- Branch: `bch-05-segmented-adapter-recovery`
- Base: `185f4bb704e7d582b0be86f560e8c3fcb98822c9`
- Original content commit: `196438a84fb6608adcd182c0bfdfe67c64b6ccc2`
- Repair commit: `a6dcc72e4abf1d018ae8c19b67d30fa87e1a9cf8`
- `Task/Common` diff: empty
- BCH-04 historical outputs: unchanged
- `git diff --check`: PASS

## Build and regression

- MinGW CMake configure: PASS
- BCH segmented build: PASS
- CTest: PASS, 4/4 (`bch15_encoder`, `bch15_syndrome_table`, `bch15_lookup_decoder`, `bch15_segmented_adapter`)
- Common regression: all six programs exit code 0, PASS

## BCH-05 repair evidence

| metric | value |
|---|---:|
| singleBlockSingleErrorCases | 705 |
| singleBlockSingleErrorMismatch | 0 |
| sameBlockDoubleErrorCases | 12 |
| reportedSuccessWrongBlockInformation | 12 |
| reportedSuccessWrongOriginalPayload | 9 |
| fillerOnlyInformationMismatch | 3 |
| postCheckFailedStateRetentionMismatch | 0 |
| unrecognizedSyndromeStateRetentionMismatch | 0 |

The single-error CSV has 705 data rows: S200 contributes 285 and S300 contributes 420. `NO_ERROR` blocks are not lookup misses. Failure-status tests verify that BCH-04 returned information bits are still concatenated while `POST_CHECK_FAILED` and `UNRECOGNIZED_SYNDROME` remain visible in block and frame details.

## Gates

- `functionalGate`: `PASS_BCH05_REPAIR`
- `auditGate`: `PASS_BCH05_AUDIT_REPAIR_EVIDENCE`
- `finalGate`: `PASS_BCH05_SEGMENTED_ADAPTER_RECOVERY`
- `mergeStatus`: `NOT_MERGED`
