# Changed files

## Added by original content commit `65ab5d9`

- `Task/BCH/README.md`: BCH work-area description.
- `Task/BCH/block/.gitkeep`, `Task/BCH/comparison/.gitkeep`: separate whole-block and comparison directory markers.
- `Task/BCH/segmented/config/.gitkeep`, `current/include/.gitkeep`, `current/src/.gitkeep`, `current/tests/.gitkeep`, `docs/.gitkeep`, `scripts/.gitkeep`: segmented BCH directory skeleton markers.
- `Task/BCH/segmented/stages/bch01_spec_parameter_freeze/acceptance_matrix.csv`: machine-readable acceptance matrix.
- `algebraic_decoder_policy.md`, `bit_polynomial_convention.md`, `lookup_decoder_policy.md`, `whole_block_policy.md`: decoder and mathematical policy freezes.
- `bch_parameter_profiles.csv`, `frozen_config.csv`, `noise_and_rate_policy.md`, `padding_recovery_policy.md`, `segmented_block_policy.md`: case, rate, filler, and segmentation freezes.
- `common_integration_contract.md`, `common_interface_audit.md`: repository-verified Common contract and audit.
- `matlab_validation_plan.md`: deferred independent validation plan.
- `stage_plan.md`, `validation_report.md`, `known_issues.md`, `commands_used.md`, `manifest.json`, `git_commit.txt`, `changes.patch`, `changed_files.md`: Stage audit records.

## Added or modified by repair content commit `e4a348c`

- `Task/BCH/AGENTS.md`: BCH-local rules; force-added because `.gitignore` otherwise ignores it.
- `noise_and_rate_policy.md`: corrects denominator membership and lists all four frame rates.
- `lookup_decoder_policy.md`, `acceptance_matrix.csv`, `matlab_validation_plan.md`, `common_integration_contract.md`, `frozen_config.csv`: freeze `syndrome=0 -> NO_ERROR`, nonzero-only lookup, and `entryCount=15`.

## Audit metadata commit

- `changed_files.md`, `git_commit.txt`, `manifest.json`, `validation_report.md`, `commands_used.md`, `changes.patch`, and `known_issues.md`: final reconciliation with actual commits, tests, remote push, and the generated main-to-branch patch.

No existing file is deleted. No `Task/Common`, BCH algorithm source, test implementation, runner, build artifact, or simulation result is added or modified.
