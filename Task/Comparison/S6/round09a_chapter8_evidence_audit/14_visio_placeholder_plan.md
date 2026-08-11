# Round09-A Visio Placeholder Plan

Chapter 8 currently contains a TODO that mentions a missing Visio comparison figure. Round09-A is not authorized to edit the report or create final presentation art, so this file records a controlled placeholder plan.

## Proposed Figure

Working title:
`译码算法比较图`

Recommended placement:
Chapter 8 cross-family summary section, after BCH/CC/LDPC individual evidence has been introduced.

## Required Inputs

- `Task/Comparison/S6/S6_metric_summary.csv`
- `Task/Comparison/S6/results/summary/figures/*/figure_data.csv`
- `Task/Comparison/S6/round09a_chapter8_evidence_audit/09_complexity_definition.csv`
- `Task/Comparison/S6/round09a_chapter8_evidence_audit/10_latency_definition.csv`

## Recommended Content

The figure should show three lanes:

1. BCH:
   - Segmented BCH-S200 with syndrome lookup.
   - Whole-block shortened BCH-B200 with BM/Chien decoding.
   - Family-specific counters: syndrome, table lookup, BM, Chien, GF arithmetic.

2. Convolutional code:
   - Block Viterbi and continuous/sliding-window Viterbi.
   - Hard and float-soft input precision.
   - Family-specific counters: ACS and traceback operations.

3. LDPC:
   - BG2 Direct QC-LDPC N560.
   - Layered BP and layered NMS.
   - Family-specific counters: message updates, check-node/variable-node updates, NMS min/sign/alpha operations.

## Mandatory Caption Notes

- Es/N0 is the primary x-axis convention for S6 Chapter 8 figures.
- CC formal evidence is integrated from historical S3 Stage14 data and was not rerun under strict pair-stop in S6.
- LDPC formal evidence is N560; N480 and N640 are recorded as case metadata but are not part of the S6 formal comparison curves.
- Complexity counters are not a single universal unit across families.

## Audit Decision

Status: PLACEHOLDER_READY.

Round09-A provides enough audited numeric and source evidence to draw the figure later, but no final Visio artifact is generated or inserted in this round.
