# Round09-A Blocking Issues

## Blocking Issues

None found for the requested evidence audit scope.

## Non-Blocking Limitations To Preserve

1. Chapter 8 report text is still a TODO in `Report/sections/08_译码算法对比.tex`.
   - Round09-A was read-only for the report and was not authorized to edit LaTeX.
   - This is not a Round09-A audit blocker, but it is a downstream writing task.

2. The CC evidence is integrated from historical S3 Stage14 formal data.
   - S6 did not rerun CC formal experiments under strict pair-stop.
   - Chapter 8 must state this limitation when using CC formal evidence.

3. LDPC formal curves use N560 only.
   - N480 and N640 exist in S4 case metadata and frozen config.
   - They are not part of the S6 formal comparison curves.

4. Cross-family complexity counters are family-specific.
   - BCH, CC and LDPC operation counters should not be merged into one universal operation count without a new normalization rule.
   - Wall-clock timing and memory are more directly comparable, subject to the recorded environment and implementation scope.

5. `S6_metric_summary.csv` does not contain P95 or P99 latency columns.
   - P95/P99 evidence exists in the final figure data/source CSVs where plotted, especially BCH latency figures.
   - Chapter 8 should not claim P95/P99 values from `S6_metric_summary.csv`.

## Final Blocker Decision

No blocker prevents closing Round09-A as a formal evidence audit.
