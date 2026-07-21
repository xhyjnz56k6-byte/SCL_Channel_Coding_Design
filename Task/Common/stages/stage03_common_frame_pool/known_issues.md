# Known Issues

No known Common-03 blocking issues.

## Remaining Scope Limits

- Large 50000-frame formal frame pools are not committed.
- `Task/Common/build/stage03/` contains generated smoke fixtures only and is not submitted.
- MATLAB reader parity is documented as a later integration activity; Common-03 validates C++ and Python bit-for-bit agreement.
- Common-04 random noise has not started.

## Preserved Workspace State

- `Task/Common/Plan/` remains untracked and unsubmitted.
- `Task/Common/build/` remains generated output and unsubmitted.
- `Task/Common/scripts/__pycache__/` remains generated cache and unsubmitted.
- User-side `AGENTS.md` and `初始规划/*.md` workspace states remain unstaged.
