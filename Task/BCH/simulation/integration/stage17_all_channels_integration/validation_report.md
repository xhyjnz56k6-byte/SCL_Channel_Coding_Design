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
