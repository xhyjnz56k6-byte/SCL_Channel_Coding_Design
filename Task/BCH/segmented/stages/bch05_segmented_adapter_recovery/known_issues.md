# BCH-05 known issues

- No BCH-06 work was started.
- No BPSK, AWGN, noise, MATLAB validation, whole-frame BCH, BM, Chien search, interleaving, or BER/FER runner was added.
- Same-block double-error cases are audit classifications only. BCH(15,11,1) is a single-error-correcting code; double errors may be miscorrected, and `CORRECTED_SINGLE_ERROR` is not treated as truth recovery.
- Group summary `Task/BCH/docs/groups/group01_segmented_core_summary.md` is not generated in this branch because BCH-05 has not yet been merged into `main`.

No unresolved BCH-05 functional issue remains. The repair commit extends the single-error audit to all 705 positions and records padded-information truth separately from original-payload truth. The audit metadata commit is created after this metadata refresh; `main` remains unmerged.
