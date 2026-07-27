# BCH S2-test archive known issues

- The archive is a path reorganization, not a new formal S2 experiment.
- Shared AWGN and case-adapter files were intentionally retained in their
  original location pending broader dependency review.
- Historical Stage manifests still describe their original functional
  commit ranges; the archive audit must not rewrite those historical ranges.
- Local results are ignored by Git and are verified separately by the
  migration audit.
- No claim is made here that original or corrected S2 results are the final
  coding-scheme selection.
