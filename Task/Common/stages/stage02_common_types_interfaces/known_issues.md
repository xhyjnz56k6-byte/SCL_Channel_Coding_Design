# Known Issues

No known Common-02 blocking issues.

## Common-02 Scope Exclusions

The following items are intentionally not implemented in Common-02:

- Common-03 frame pool generation and reader implementation.
- BPSK mapping.
- AWGN channel.
- Standard Gaussian noise generation.
- Sigma or LLR computation.
- BER/FER statistics.
- Wilson interval.
- Stop controller.
- Checkpoint/resume I/O.
- BCH, convolutional-code, Viterbi, LDPC, BP, or NMS algorithms.

## Preserved Workspace State

These user/workspace states are intentionally not staged by Common-02:

- `Task/Common/Plan/` remains untracked and unsubmitted.
- `Task/Common/build/` remains generated output and unsubmitted.
- Two `初始规划/*.md` deleted-file states are preserved and unsubmitted.
- `AGENTS.md` contains user-side local changes and is not staged by this audit closure.

## Merge Status

The current branch is not merged into `main`.
