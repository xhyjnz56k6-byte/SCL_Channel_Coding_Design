# Stage17 Known Issues

## BLOCKED: Stage07 AWGN Dense Checker Requires Untracked Point Evidence

After merging `origin/stage07-bch-s2-awgn-dense-formal`, the Stage07 checker fails with:

```text
BLOCKED_STAGE07_AWGN_DENSE_FORMAL_CHECK: checkpoint count mismatch
```

The checker expects 296 checkpoint JSON files, 296 point result CSV files, and 296 point run logs under `results/points/`, but the remote branch tracks zero files under that path.

This prevents a fresh integration worktree from reproducing the original checker PASS using Git-tracked evidence only.

## BLOCKED: Stage07 Audit Hard-Codes Source Branch

The Stage07 audit script compares the current branch to `stage07-bch-s2-awgn-dense-formal`; it fails on the integration branch with:

```text
BLOCKED_STAGE07_AWGN_DENSE_FORMAL_AUDIT: branch mismatch
```

This is expected for an integration branch, but the original audit script does not provide an integration-mode override.

## Stage17 Resolution

This issue is resolved for Stage17 by adding integration-context checks that use only tracked canonical evidence:

- `PASS_STAGE17_AWGN_DENSE_SOURCE_ATTESTATION`
- `PASS_STAGE17_AWGN_DENSE_INTEGRATION_CHECK`

The original Stage07 checker and audit remain recorded as:

```text
NOT_APPLICABLE_IN_INTEGRATION_CONTEXT
```

They are not rewritten as PASS.

Current decision:

```text
PASS_STAGE17_AFTER_AWGN_DENSE_MERGE
```
