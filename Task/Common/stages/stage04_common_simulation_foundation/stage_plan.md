# Common-04 Stage Plan: Shared Simulation Foundation

## Goal

Common-04 defines and validates the shared simulation foundation used after Common-03 frame pools and before concrete BCH, convolutional-code, or LDPC decoders.

This Stage covers:

- Deterministic random key derivation for standard Gaussian mother noise.
- Standard Gaussian noise generation and optional small noise-pool generation.
- Versioned noise-pool manifest, binary shard header, SHA256 and overallHash.
- BPSK, AWGN, hard decision and LLR.
- BER, FER, successRate, latency metrics and stop control.
- checkpoint/resume, frame-shard execution/merge, CSV/JSON result schema.
- Common PNG plotting utility.
- identity codec integration for K=200 and K=300.
- Common-02 and Common-03 regression.

Final Gate:

```text
PASS_COMMON_SIMULATION_FOUNDATION
```

## Non-Goals

Common-04 must not implement:

- BCH encoding or decoding.
- Convolutional encoding or Viterbi decoding.
- LDPC encoding, Layered BP, NMS, OMS or MS.
- CRC, filler recovery, rate matching, interleaving or deinterleaving.
- Burst-error, multipath, frequency-offset, Doppler or blockage channels.
- MATLAB codec comparison.
- Common-05 or any BCH/CC/LDPC Stage.

## Scope

Allowed modifications:

- `Task/Common/include/common/`
- `Task/Common/src/`
- `Task/Common/scripts/`
- `Task/Common/tests/stage04/`
- `Task/Common/config/`
- `Task/Common/stages/stage04_common_simulation_foundation/`
- `Task/Common/CMakeLists.txt`
- Necessary registration in `Task/Common/include/common/common.hpp`
- Necessary and precise `.gitignore`

Compatibility exception:

- `Task/Common/scripts/check_common02.py`
- `Task/Common/scripts/check_common03.py`

These old checker files may be changed only for minimal compatibility with the new branch/audit model. Common-01, Common-02 and Common-03 frozen functionality must not be changed.

Forbidden submitted scope:

- `Task/Common/Plan/`
- `Task/Common/build/`
- Large `Task/Common/results/`
- `Task/BCH/`
- `Task/CC/`
- `Task/LDPC/`
- `initial planning` folders such as `初始规划/`
- Large frame pools
- Large noise pools
- formal checkpoints
- `.exe`, `.obj`, `.pdb`, `.pyc`
- `__pycache__/`

## Frozen Decisions

- `noiseDomainSeparator` is frozen in `frozen_config.csv` and must be used by the noise key. It separates the noise key space from the Common-03 payload key space.
- Field-change tests use a frozen finite sample set. They prove deterministic differentiation for that sample set, not a mathematical all-domain no-collision guarantee.
- Noise shards use a versioned binary header. The header must be serialized field by field; writing raw C++ struct memory is forbidden.
- C++ and Python must parse the same header bytes and agree on header fields.
- `payloadDataHash` is not part of the Common-04 noise shard header or manifest. The complete shard SHA256 and deterministic noisePoolId/overallHash cover shard identity. Frame-pool payload identity remains owned by Common-03.
- Small noise pools are generated only under `build/` or another temporary directory. Binary fixture pools are not committed by default.
- `createdTime` is runtime metadata only. It must not enter `configHash`, `noisePoolId` or noise-pool `overallHash`.
- Monte Carlo SNR trend checks are sanity checks. Higher SNR BER should be grossly non-increasing over the frozen smoke/prescan cases, but short samples are not required to be strictly monotonic point by point.
- formal capacity validation checks 50000 frames, 1000 symbols/frame and 50 shards as configuration/capacity support. It does not run full BCH/CC/LDPC formal curves and does not commit large assets.

## Internal Gates

```text
G1 = PASS_COMMON_RANDOM_POLICY
G2 = PASS_COMMON_GAUSSIAN_NOISE
G3 = PASS_COMMON_BPSK_AWGN_LLR
G4 = PASS_COMMON_METRICS_CONTROL
G5 = PASS_COMMON_CHECKPOINT_RESULTS
G6 = PASS_COMMON_INTEGRATION
```

Gate order:

1. G1 must pass before G2.
2. G2 must pass before G3.
3. G3 must pass before G4.
4. G4 must pass before G5.
5. G5 must pass before G6.
6. G6 must pass before final audit closure.

Any failed Gate stops the Stage. Do not skip tests, delete failing tests, or mark unexecuted tests as PASS.

## Stage Records

Default lightweight audit files:

- `stage_plan.md`
- `acceptance_matrix.csv`
- `manifest.json`
- `validation_report.md`
- `known_issues.md`
- `frozen_config.csv`
- `random_policy.md`
- `noise_pool_format.md`
- `simulation_formula.md`
- `result_schema.md`
- `cpp_python_comparison.csv`
- `negative_test_results.csv`
- `identity_baseline_results.csv`

Default non-submitted files:

- `snapshot/`
- `changes.patch`
- large noise pools
- large frame pools
- `build/`
- formal `results/`

## Audit Closure

After implementation and all Gates pass, create a functional commit. Then generate final audit files from real Git state and create an audit closure commit.

`manifest.json` must record at least:

- schemaVersion
- stage
- branch
- baseCommit
- functionalCommit
- remoteBranch
- remoteVerificationStatus
- mergeStatus
- gate
- added
- modified
- deleted

Audit files record the audited functional commit SHA. They must not record the audit commit SHA itself.

## Stop Point

Push only:

```text
origin/stage04-common-simulation-foundation
```

Then stop. Do not merge `main`. Do not start Common-05, BCH, CC, LDPC or interleaving work.
