# BCH-05 commands used

Working directory: `C:/Users/V3169/Desktop/Project/SCL_Channel_Coding_Design`

## Precheck and recovery

- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git status --short`
- `git rev-parse HEAD`
- `git rev-parse main`
- `git log --oneline --decorate -8`
- `git diff --name-status`
- `git diff -- Task/BCH/segmented/stages/bch04_lookup_decoder_audit`
- `git ls-files --others --exclude-standard`
- `git hash-object <six BCH-04 audit csv files>`
- `git restore --source=HEAD -- <six BCH-04 audit csv files>`

## Build and BCH regression

- `cmake -G "MinGW Makefiles" -S Task/BCH/segmented/current -B Task/BCH/segmented/build/bch05_adapter_recovery -DCMAKE_BUILD_TYPE=Release`
- `cmake --build Task/BCH/segmented/build/bch05_adapter_recovery`
- `ctest --test-dir Task/BCH/segmented/build/bch05_adapter_recovery --output-on-failure`

CTest registered runtime output directories:

- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch02_encoder`
- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch03_syndrome_table`
- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch04_lookup_decoder`
- `Task/BCH/segmented/build/bch05_adapter_recovery/test_outputs/bch05_segmented_adapter`

## Common regression

- `Task/Common/build/stage04/test_common04_random_policy.exe`
- `Task/Common/build/stage04/test_common04_gaussian_noise.exe`
- `Task/Common/build/stage04/test_common04_modulation_awgn.exe`
- `Task/Common/build/stage04/test_common04_metrics_control.exe`
- `Task/Common/build/stage04/test_common04_checkpoint.exe`
- `Task/Common/build/stage04/test_common04_integration.exe`

## Scope and audit checks

- `git diff --check`
- `git diff --name-only main...HEAD -- Task/Common`
- `git diff --name-status 185f4bb704e7d582b0be86f560e8c3fcb98822c9...196438a84fb6608adcd182c0bfdfe67c64b6ccc2`
- `git diff --binary --output=Task/BCH/segmented/stages/bch05_segmented_adapter_recovery/changes.patch 185f4bb704e7d582b0be86f560e8c3fcb98822c9...196438a84fb6608adcd182c0bfdfe67c64b6ccc2 -- <BCH-05 functional files>`
- `git apply --check --reverse Task/BCH/segmented/stages/bch05_segmented_adapter_recovery/changes.patch`
