# Chapter 9 section evidence map

## 9.1 Interleaving burst-error objective and chain

Figures: overview references from Stage15 A-level figures. CSV: `chapter9_figure_evidence_matrix.csv`, `chapter9_burst_channel_definition.md`. Tables: 9.1. Question: what channel and evidence chain is Chapter 9 allowed to use?

## 9.2 Fixed coding schemes, burst-error channel and interleavers

Figures: none required; use definitions. CSV: timing audit, LDPC audit, formal configs. Tables: 9.1-9.4. Question: what exactly are BCH, CC and the burst-error channel in S7?

## 9.3 BCH segmented scheme under burst errors

Use BCH figures 01-28, including duplicated numeric prefix `22_all_start_heatmap_5_percent` and `22_burst_5_ber` as distinct directories. CSV: BCH formal results and BCH rows in `chapter9_figure_evidence_matrix.csv`. Tables: 9.3, 9.5, 9.6, 9.9, 9.10. Question: how does interleaving change BCH subblock error distribution and observed FER/BER?

## 9.4 CC interleaving under burst errors

Use CC figures 01-21. CSV: CC formal results and CC rows in the evidence matrix. Tables: 9.4, 9.7, 9.8, 9.9, 9.10. Question: how do short-depth and pseudorandom trellis-step interleavers affect local trellis disturbance?

## 9.5 High-speed no-interleaving LDPC near-rate baseline

Use CC figure `22_cc_ldpc_no_burst_decode_latency` and CC figures 01-05 only as LDPC AWGN overlays. CSV: `chapter9_ldpc_baseline_audit.csv`, `S7_coding_reference_summary.csv`. Table: 9.11. Question: what can the no-burst LDPC reference say without becoming a burst or interleaver claim?

## 9.6 Combined interleaving gain and engineering cost

Use buffer, timing, improvement and tolerance figures. CSV: evidence matrix, timing audit, table plan. Tables: 9.9, 9.10, 9.12. Question: what performance-cost tradeoff is supported by existing S7 evidence?

## 9.7 Chapter conclusion

Use only conclusions already supported by the figure/data matrix. LDPC remains a no-interleaving AWGN baseline and does not enter interleaver ranking or burst tolerance extrapolation.
