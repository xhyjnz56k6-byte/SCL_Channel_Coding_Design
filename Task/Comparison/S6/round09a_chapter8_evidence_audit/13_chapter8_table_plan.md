# Round09-A Chapter 8 Table Plan

This file records table candidates for Chapter 8. It is an audit planning artifact only; it does not modify the report source.

## Table 8-1 BCH Case Definitions

Evidence sources:
- `Task/BCH/simulation/current/src/bch_case_adapter.cpp`
- `Task/BCH/simulation/current/tests/test_bch_s6_metrics.cpp`
- `Task/Comparison/S6/results/bch/formal_v02_20260804/execution_environment.json`

Recommended columns:
- Case
- Payload bits
- Codeword bits
- Effective rate
- Construction
- Decoder
- Error-correction capability
- Formal timing scope

Audit status: READY.

## Table 8-2 BCH Performance and Resource Summary

Evidence sources:
- `Task/Comparison/S6/S6_metric_summary.csv`
- `Task/Comparison/S6/results/summary/figures/bch_*/figure_data.csv`
- `Task/Comparison/S6/round09a_chapter8_evidence_audit/11_fer_threshold_audit.csv`

Recommended columns:
- Case
- Total frames
- BER/FER threshold crossing values if used
- Weighted average decode time
- Maximum observed decode time
- Decoder memory bytes
- Zero BER/FER point counts

Audit status: READY.

## Table 8-3 Convolutional Code Scheme Definitions

Evidence sources:
- `Task/Comparison/S6/results/cc/cc_source_inventory.csv`
- `Task/Comparison/S6/results/cc/cc_integration_summary.json`
- `Task/CC/simulation/stages/S3/stage14_block_continuous_comparison/src/stage14_runner.cpp`

Recommended columns:
- Scheme
- Decision mode
- Input precision
- Payload bits
- Transmitted bits
- Actual rate
- Window length
- Slide step
- Traceback depth
- Formal source stage

Audit status: READY_WITH_LIMITATION.

Mandatory limitation note:
The CC evidence was selected from historical S3 Stage14 formal data. S6 did not rerun CC formal experiments under a strict pair-stop policy. Chapter 8 must preserve this limitation.

## Table 8-4 Convolutional Code Summary Metrics

Evidence sources:
- `Task/Comparison/S6/S6_metric_summary.csv`
- `Task/Comparison/S6/results/summary/figures/cc_*/figure_data.csv`
- `Task/Comparison/S6/round09a_chapter8_evidence_audit/11_fer_threshold_audit.csv`

Recommended columns:
- Scheme
- Total frames
- Weighted average decode time
- Maximum observed decode time
- Decoder memory bytes
- Zero BER/FER point counts
- ACS or traceback complexity descriptor

Audit status: READY_WITH_LIMITATION.

## Table 8-5 LDPC Case Definition

Evidence sources:
- `Task/LDPC/block/stages/stage23_s4_final_reintegration/frozen_config.csv`
- `Task/LDPC/block/stages/stage23_s4_final_reintegration/results/s4_revised_case_metadata.csv`
- `Task/LDPC/block/current/src/s4_ldpc.cpp`

Recommended columns:
- Selected formal case
- Payload bits
- Actual length
- Actual rate
- Zc
- Filler bits
- Parity bits
- Rank Hp
- Decoder variants
- Maximum iterations
- Early-stop policy
- NMS alpha

Audit status: READY.

Mandatory clarification:
The nominal S4 target length 576 maps to actual formal case N560 through the direct BG2 candidate selector. Chapter 8 should call the plotted case N560, not N576.

## Table 8-6 LDPC Summary Metrics

Evidence sources:
- `Task/Comparison/S6/S6_metric_summary.csv`
- `Task/Comparison/S6/results/summary/figures/ldpc_*/figure_data.csv`
- `Task/Comparison/S6/round09a_chapter8_evidence_audit/11_fer_threshold_audit.csv`

Recommended columns:
- Decoder
- Total frames
- Weighted average decode time
- Maximum observed decode time
- Decoder memory bytes
- Average iteration range or selected points
- Zero BER/FER point counts

Audit status: READY.

## Table 8-7 Cross-Family Metric Summary

Evidence source:
- `Task/Comparison/S6/S6_metric_summary.csv`

Recommended columns:
- Family
- Representative scheme
- Total frames
- Weighted average decode time
- Maximum observed decode time
- Decoder memory bytes
- Notes on metric comparability

Audit status: READY_WITH_SCOPE_NOTE.

Scope note:
Cross-family comparison must not imply identical decoder internals or identical complexity units. Time and memory are the safest direct comparison fields; operation counters remain family-specific.
