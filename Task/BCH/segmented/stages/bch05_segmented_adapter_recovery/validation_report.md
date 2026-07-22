# BCH-05 validation report

## Git and output isolation

- Branch: `bch-05-segmented-adapter-recovery`
- Start/base commit: `185f4bb704e7d582b0be86f560e8c3fcb98822c9`
- Content commit: `196438a84fb6608adcd182c0bfdfe67c64b6ccc2`
- Restored BCH-04 historical outputs:
  - `double_error_audit.csv`
  - `multi_error_seed_audit.csv`
  - `no_error_summary.csv`
  - `single_error_summary.csv`
  - `status_summary.csv`
  - `test_summary.csv`
- BCH-04 hash before and after CTest:
  - `c12bae2b06267fe98f15ee083b6021e9bae4157e`
  - `fe2549846d407535cbc04f39f324c24329ad744d`
  - `e6ebc9df57e997a40b6f2a95bc17ab376a32e303`
  - `bd3bf09a3924aebf090463a1a9b6a404ee99c61c`
  - `1c5f1ea93239da0b952ad4fb7031d4f5c07df79c`
  - `dcb28f88ce48c5c63dab217a98a2afa39433f23e`
- Output isolation: `PASS_BCH05_TEST_OUTPUT_ISOLATION`

## Build and CTest

- CMake configure: PASS
- Build: PASS
- CTest: PASS, 4/4
  - `bch15_encoder`: PASS
  - `bch15_syndrome_table`: PASS
  - `bch15_lookup_decoder`: PASS
  - `bch15_segmented_adapter`: PASS

CTest output directory: `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs`

## BCH-05 functional evidence

- BCH-S200: payloadLength=200, blockCount=19, fillerBits=9, encodedLength=285, codeRate=200/285, last block=2 payload + 9 filler.
- BCH-S300: payloadLength=300, blockCount=28, fillerBits=8, encodedLength=420, codeRate=300/420, last block=3 payload + 8 filler.
- Synthetic noiseless frames: 8, payload mismatch=0.
- Common pool frames: 200, payload mismatch=0.
- Single block single-error audit: 255 cases, mismatch=0.
- Multi-block single-error audit: 8 cases, mismatch=0.
- Same-block double-error audit: 12 cases classified.
- Same-block double-error payload recovered cases: 3.
- Same-block double-error reported-success but block-truth-wrong cases: 12.
- Filler boundary audit: 30 cases, mismatch=0.
- Invalid input failures: 0.

## Common regression

All six Common binaries returned exit code 0:

| program | exit code | result |
|---|---:|---|
| `Task/Common/build/stage04/test_common04_random_policy.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_gaussian_noise.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_modulation_awgn.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_metrics_control.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_checkpoint.exe` | 0 | PASS |
| `Task/Common/build/stage04/test_common04_integration.exe` | 0 | PASS |

## Scope checks

- `git diff --check`: PASS.
- `git diff --name-only main...HEAD -- Task/Common`: empty.
- No BCH-06 implementation files were added.
- No AWGN, BPSK, MATLAB validation, whole-frame BCH, BM, Chien, interleaver, or BER/FER runner was implemented in BCH-05.
- `changes.patch`: real diff from base commit to content commit, reverse apply check PASS.

## Gates

- `functionalGate`: `PASS_BCH05_SEGMENTED_ADAPTER_RECOVERY_FUNCTIONAL`
- `auditGate`: `PASS_BCH05_AUDIT_FINALIZED`
- `finalGate`: `PASS_BCH05_SEGMENTED_ADAPTER_RECOVERY`
