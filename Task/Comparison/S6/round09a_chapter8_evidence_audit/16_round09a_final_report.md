# Round09-A Final Report

## Scope

Round09-A audited the evidence needed to write Chapter 8, "译码算法对比", from existing S6 formal artifacts. The audit was restricted to evidence inspection and audit archive creation.

## Repository State

- Repository root: `C:\Users\V3169\Desktop\Project\SCL_Channel_Coding_Design`
- Branch: `S8-PaperDocu`
- Starting HEAD: `e378ffeb03427d2c261b136fe32ce8e42c1a25ee`
- Commit/push: not performed
- Main merge: not performed

## Created Audit Archive

Archive directory:
`Task/Comparison/S6/round09a_chapter8_evidence_audit`

Files:
- `readme.txt`
- `01_git_state.txt`
- `02_asset_inventory.csv`
- `03_figure_evidence_map.csv`
- `04_snr_convention_audit.md`
- `05_bch_evidence_audit.md`
- `06_cc_evidence_audit.md`
- `07_ldpc_evidence_audit.md`
- `08_metric_summary_semantics.md`
- `09_complexity_definition.csv`
- `10_latency_definition.csv`
- `11_fer_threshold_audit.csv`
- `12_chapter8_figure_layout_plan.csv`
- `13_chapter8_table_plan.md`
- `14_visio_placeholder_plan.md`
- `15_blocking_issues.md`
- `16_round09a_final_report.md`

## Evidence Audited

1. Final S6 figure assets:
   - 26 figure directories under `Task/Comparison/S6/results/summary/figures`.
   - Each directory contains `figure.png`, `figure_data.csv`, `plot_manifest.json`, and `readme.txt`.
   - Manifest hashes for PNGs, figure data, and source CSVs were checked.

2. SNR convention:
   - S6 final figures use `esN0Db` as the primary x-axis where SNR appears.
   - BCH, CC and LDPC source code each use sigma squared `1/(2*10^(Es/N0/10))` for the AWGN noise convention.

3. Zero-value plotting policy:
   - Log-scale zero rows are preserved in `figure_data.csv`.
   - Plot columns leave `plotValue` empty and set `isPlotted=false`.
   - No smoothing, interpolation, or extrapolation is recorded in final figure manifests.

4. BCH evidence:
   - BCH-S200 is segmented BCH(15,11)-style decoding with syndrome lookup across 19 segments.
   - BCH-B200 is a shortened whole-block BCH decoder using BM/Chien structure.
   - Timing, complexity and memory evidence are traceable to BCH formal S6 outputs and source code.

5. CC evidence:
   - CC evidence is S6 integration of S3 Stage14 formal data.
   - The audit preserves the limitation that CC was not rerun under strict pair-stop in S6.
   - Hard and float-soft Viterbi evidence, block and continuous variants, are mapped from the integration inventory and runner source.

6. LDPC evidence:
   - S6 formal LDPC comparison uses BG2 Direct QC-LDPC N560.
   - BP and NMS share payload/codeword/LLR evidence at paired SNR points.
   - Early stop is syndrome-after-full-iteration; max iterations are 32; NMS alpha is 0.95.

7. Metric summary semantics:
   - `totalFrames`, `totalBitErrors`, and `totalFrameErrors` are sums across SNR points.
   - `weightedAvgDecodeTimeUs` is frame-weighted across SNR points.
   - `maxObservedDecodeTimeUs` is the maximum observed point max.
   - `decoderMemoryBytes` is a model/reported memory field.
   - P95/P99 latency is not part of `S6_metric_summary.csv`.

## Checks Performed

- Git state recorded before audit archive creation.
- Figure inventory counted and classified by family.
- Machine hash audit checked figure PNG hashes, figure_data hashes and source CSV hashes against `plot_manifest.json`.
- Machine policy audit checked final manifests for `interpolation=NONE`, `smoothing=NONE`, and no extrapolation.
- Zero-value log plotting behavior was checked from final figure data.
- FER threshold crossing audit generated from final figure CSV evidence.
- Source-level evidence was inspected for BCH, CC and LDPC timing, channel, decoder and metric semantics.

## Gate Matrix

| Gate | Result |
|---|---|
| Current branch is not `main` | PASS |
| No formal simulation rerun | PASS |
| Existing formal data, figures, source, plot scripts and LaTeX left unchanged | PASS |
| 26 final S6 figure directories found | PASS |
| Figure hashes match manifests | PASS |
| Source CSV hashes match manifests | PASS |
| No smoothing/interpolation/extrapolation in final S6 figure manifests | PASS |
| Zero log-scale values preserved rather than fabricated | PASS |
| FER threshold audit produced machine-readable evidence | PASS |
| BCH evidence chain traced to source, formal data and final figures | PASS |
| CC evidence chain traced with non-strict pair-stop limitation preserved | PASS |
| LDPC evidence chain traced to N560 BP/NMS formal comparison | PASS |
| Chapter 8 figure/table/Visio plans created without editing report LaTeX | PASS |

## Known Issues

No blocking issue was found for Round09-A.

Non-blocking limitations are recorded in `15_blocking_issues.md` and must be preserved in Chapter 8 writing.

## Final Decision

PASS_ROUND09_A_S6_CHAPTER8_FORMAL_EVIDENCE_AUDIT
