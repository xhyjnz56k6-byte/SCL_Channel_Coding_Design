# Known Issues

No known Common-03 blocking issues.

## Intentional Exclusions

Common-03 does not implement:

- BPSK.
- AWGN.
- Standard Gaussian noise.
- Sigma or LLR computation.
- BER/FER statistics.
- Wilson intervals.
- Stop controller.
- Checkpoint/resume I/O.
- BCH, convolutional-code, Viterbi, LDPC, BP, or NMS algorithms.

## Generated Data

The checker generates small temporary frame pools under `Task/Common/build/stage03/`.
These are validation artifacts and are not submitted.

## Preserved Workspace State

- `Task/Common/Plan/` remains untracked and unsubmitted.
- `Task/Common/build/` remains generated output and unsubmitted.
- `Task/Common/scripts/__pycache__/` remains generated Python cache and unsubmitted.
- Two `初始规划/*.md` deleted-file states are preserved and unsubmitted.
- `AGENTS.md` contains user-side local changes and is not staged by Common-03.

## Merge Status

The current branch is not merged into `main`.
