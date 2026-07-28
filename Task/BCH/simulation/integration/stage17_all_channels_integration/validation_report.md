# Stage17 BCH S2 All Channels Integration Validation Report

## Current Status

Gate: `PASS_STAGE17_AFTER_AWGN_DENSE_MERGE`

Integration branch: `stage17-all-channels-integration`

Integration worktree:
`C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_stage17_integration`

Base commit: `069373b02401ad0acc10d96eb4e63bad8763c64c`

First merge commit: `eb695b8`

## Completed

- Generated branch inventory:
  `results/stage17_all_channels_integration_branch_inventory.csv`
- Generated dependency graph:
  `results/stage17_all_channels_integration_dependency_graph.md`
- Merged `origin/stage07-bch-s2-awgn-dense-formal`.

The AWGN dense branch already contains the AWGN Stage01-06 base branch.

## Executed Regression

Command:

```text
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_check.py
```

Result:

```text
BLOCKED_STAGE07_AWGN_DENSE_FORMAL_CHECK: checkpoint count mismatch
```

Command:

```text
python Task\BCH\simulation\stages\S2\stage07_awgn_dense_formal\python\stage07_awgn_dense_formal_audit.py
```

Result:

```text
BLOCKED_STAGE07_AWGN_DENSE_FORMAL_AUDIT: branch mismatch
```

## Blocking Cause

`stage07_awgn_dense_formal_check.py` requires 296 point-level checkpoint JSON files, 296 point result CSV files, and 296 point run logs under:

```text
Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal/results/points/
```

The remote branch contains zero tracked files under that path:

```text
git ls-tree -r --name-only origin/stage07-bch-s2-awgn-dense-formal Task/BCH/simulation/stages/S2/stage07_awgn_dense_formal/results/points
```

Therefore the original Stage07 checker cannot pass in a fresh integration worktree that uses only tracked Git content.

`stage07_awgn_dense_formal_audit.py` also hard-codes the original feature branch name from the Stage07 manifest, so it reports `branch mismatch` on the integration branch.

## Stage17 Integration-Context Checks

Command:

```text
python Task\BCH\simulation\integration\stage17_all_channels_integration\stage17_awgn_dense_source_attestation.py
```

Result:

```text
PASS_STAGE17_AWGN_DENSE_SOURCE_ATTESTATION
```

Command:

```text
python Task\BCH\simulation\integration\stage17_all_channels_integration\stage17_awgn_dense_integration_check.py
```

Result:

```text
EPHEMERAL_POINT_EVIDENCE_NOT_TRACKED_AS_DESIGNED
PASS_STAGE17_AWGN_DENSE_INTEGRATION_CHECK
```

## Evidence Interpretation

The original Stage07 checker and audit are not marked as PASS in this integration context.

- `stage07_awgn_dense_formal_check.py`: `NOT_APPLICABLE_IN_INTEGRATION_CONTEXT`
- `stage07_awgn_dense_formal_audit.py`: `NOT_APPLICABLE_IN_INTEGRATION_CONTEXT`

The failure is caused by worktree-context assumptions: untracked point-level runtime evidence and original-branch-only audit assertions. It is not a numeric failure of the canonical formal results.

No point-level checkpoint JSON files, point CSV files, or point logs were copied from another worktree or committed.

## Gate Decision

Stage17 may proceed to the next merge after AWGN dense.

Generated step Gate:

```text
PASS_STAGE17_AFTER_AWGN_DENSE_MERGE
```

No `PASS_BCH_S2_ALL_CHANNELS_INTEGRATION` has been generated yet.

No merge to `main` has been attempted.

No push has been attempted.

## Multipath Common-SNR Merge

Merged branch:

```text
origin/stage07-08-bch-s2-multipath
```

Merge commit:

```text
7ffff868de786a1fca2bcad1530c9431b2b6eb87
```

Executed regressions:

```text
python Task\BCH\simulation\stages\S2\stage08_multipath_formal_common_snr\python\stage08_multipath_formal_common_snr_check.py
PASS_STAGE08_COMMON_SNR_RESULTS_CHECK points=296 frames=5599111

python Task\BCH\simulation\stages\S2\stage08_multipath_formal_common_snr\python\stage08_multipath_formal_common_snr_plot_check.py
PASS_STAGE08_COMMON_SNR_PLOT_CHECK

python Task\BCH\simulation\stages\S2\stage08_multipath_formal_common_snr\python\stage08_multipath_formal_common_snr_finalize_audit.py
PASS_STAGE08_MULTIPATH_COMMON_SNR_COMPARISON
```

The finalize audit script temporarily refreshed Stage08 audit files for the integration HEAD. Those run-side effects were restored and were not committed, because Stage17 must not rewrite original Stage08 audit evidence during integration.

Generated step Gate:

```text
PASS_STAGE17_AFTER_MULTIPATH_MERGE
```

## CFO And Blockage Base Merge

Merged branch:

```text
origin/stage09-12-bch-s2-cfo-blockage
```

The first merge attempt was blocked by Windows long path handling for two Stage12 Experiment C manifest filenames. The failed merge did not create `MERGE_HEAD`; the four untracked Stage09-12 directories created by that failed attempt were removed after path verification, `core.longpaths=true` was set for this repository, and the merge was retried successfully.

Merge commit:

```text
f2263c06ac5a663d3b46efb0ea8f46b446b07b67
```

Executed regressions:

```text
python Task\BCH\simulation\stages\S2\stage09_cfo_validation\python\stage09_cfo_validation_checker.py
PASS_STAGE09_CFO_VALIDATION

python Task\BCH\simulation\stages\S2\stage10_cfo_formal\python\stage10_cfo_formal_checker.py
PASS_STAGE10_CFO_FORMAL

python Task\BCH\simulation\stages\S2\stage11_blockage_validation\python\stage11_blockage_validation_checker.py
PASS_STAGE11_BLOCKAGE_VALIDATION

python Task\BCH\simulation\stages\S2\stage12_blockage_formal\python\stage12_blockage_formal_checker.py
PASS_STAGE12_BLOCKAGE_FORMAL

python \\?\C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design_stage17_integration\Task\BCH\simulation\stages\S2\stage12_blockage_formal\experiment_c_fixed_length\python\stage12_blockage_formal_experiment_c_fixed_length_checker.py
PASS_STAGE12_BLOCKAGE_FORMAL_EXPERIMENT_C_FIXED_LENGTH
```

Generated step Gate:

```text
PASS_STAGE17_AFTER_CFO_BLOCKAGE_BASE_MERGE
```

## CFO And Blockage Dense-SNR Merge

Merged branch:

```text
origin/stage10-12-bch-s2-dense-snr-rerun
```

Merge commit:

```text
b0fce2e163b8ce4964d4e8c1e411130a2c45f9ca
```

Executed regressions:

```text
python Task\BCH\simulation\stages\S2\stage10_cfo_formal\python\stage10_cfo_formal_checker.py
PASS_STAGE10_CFO_FORMAL

python Task\BCH\simulation\stages\S2\stage12_blockage_formal\python\stage12_blockage_formal_checker.py
PASS_STAGE12_BLOCKAGE_FORMAL_DENSE_SNR
```

Generated step Gate:

```text
PASS_STAGE17_AFTER_CFO_BLOCKAGE_DENSE_MERGE
```

## Burst And Interleaving Merge

Merged branch:

```text
origin/stage13-16-bch-s2-burst-interleaving
```

Merge commit:

```text
324f7a6367b090adcba8c2628c153fa0c01611ad
```

Executed regressions:

```text
python Task\BCH\simulation\stages\S2\stage13_burst_interleaving_validation\python\stage13_burst_interleaving_validation_check.py
PASS_STAGE13_BURST_INTERLEAVING_VALIDATION_FUNCTIONAL

python Task\BCH\simulation\stages\S2\stage14_burst_formal\python\stage14_burst_formal_check.py
PASS_STAGE14_BURST_FORMAL_FUNCTIONAL

python Task\BCH\simulation\stages\S2\stage15_interleaving_formal\python\stage15_interleaving_formal_check.py
PASS_STAGE15_INTERLEAVING_FORMAL_FUNCTIONAL

python Task\BCH\simulation\stages\S2\stage16_burst_interleaving_comparison\python\stage16_burst_interleaving_comparison_check.py
PASS_STAGE16_BURST_INTERLEAVING_COMPARISON_FUNCTIONAL
PASS_BCH_S2_BURST_INTERLEAVING_STAGE13_TO_STAGE16_FUNCTIONAL
```

Additional evidence:

```text
PASS_STAGE16_PLOT_REVISION
origin/stage13-16-bch-s2-burst-interleaving is ancestor of HEAD
```

The Stage13-16 checkers temporarily refreshed original Stage files with functional Gate wording. Those run-side effects were restored and were not committed; Stage17 records the observed checker outputs.

Generated step Gate:

```text
PASS_STAGE17_AFTER_BURST_INTERLEAVING_MERGE
```

## Full Integration Check

Ancestor checks:

```text
origin/stage07-bch-s2-awgn-dense-formal ancestor of HEAD: PASS
origin/stage07-08-bch-s2-multipath ancestor of HEAD: PASS
origin/stage10-12-bch-s2-dense-snr-rerun ancestor of HEAD: PASS
origin/stage13-16-bch-s2-burst-interleaving ancestor of HEAD: PASS
```

Forbidden module diff:

```text
Task/CC changes: 0
Task/LDPC changes: 0
```

Full whitespace check:

```text
git diff --check origin/main...HEAD
```

Result:

```text
BLOCKED_STAGE17_FULL_DIFF_CHECK
```

Blocking files include:

- `Task/BCH/simulation/stages/S2/stage08_multipath_formal_common_snr/stage08_multipath_formal_common_snr_error_floor_repair.patch`
- `Task/BCH/simulation/stages/S2/stage13_burst_interleaving_validation/...`
- `Task/BCH/simulation/stages/S2/stage14_burst_formal/...`
- `Task/BCH/simulation/stages/S2/stage15_interleaving_formal/...`

The errors are pre-existing content from merged source branches: trailing whitespace in a retained patch evidence file and new blank lines at EOF in Burst/Interleaving source or config files.

Gate decision:

```text
BLOCKED_BCH_S2_ALL_CHANNELS_INTEGRATION_FULL_DIFF_CHECK
```

`PASS_BCH_S2_ALL_CHANNELS_INTEGRATION` has not been generated.
