# Stage15 CC S3 revision validation report

## Scope

This validation covers the strict CC S3 revision on top of the existing Stage01-Stage15 implementation. The formal payload length remains 300 bits. No 200-bit formal simulation was added.

## Commands executed

- `python Task/CC/simulation/stages/S3/stage09_awgn_formal/build/stage09_awgn_formal_runner.exe ... --grid two-level-coarse --shard-count 4`
- `python Task/CC/simulation/stages/S3/stage10_traceback_study/scripts/run_stage10.py --clean`
- `python Task/CC/simulation/stages/S3/stage11_soft_quantization/scripts/run_stage11.py --clean`
- `python Task/CC/simulation/stages/S3/stage13_sliding_window_viterbi/scripts/run_stage13.py --clean`
- `python Task/CC/simulation/stages/S3/stage14_block_continuous_comparison/scripts/run_stage14.py --clean`
- `python Task/CC/simulation/stages/S3/stage15_cc_s3_integration/scripts/run_stage15.py`

## Results

- Stage01-Stage15 Chinese `readme.txt`: PASS, 15 files present.
- Stage09 two-level SNR grid: PASS. Coarse layer has 186 real rerun points for 6 cases over -5.0 to 10.0 dB in 0.5 dB steps. Dense layer has 126 verified legacy waterfall points. Merged layer keeps dense points when duplicate SNR points exist.
- Stage10 traceback audit and rerun: PASS. Existing data audit is DATA_PARTIAL, expanded rerun covers Dtb=35,49,70,84,98,112 plus full traceback reference. Recommended Dtb is 84 with PREFERRED tier.
- Stage11 quantization audit and rerun: PASS. Existing data audit is DATA_VALID. Float/Q3/Q4/Q6 are independently decoded; Q6 is recommended.
- Stage12 continuous encoder regression: PASS.
- Stage13 true sliding-window Viterbi: PASS. Window, slide and traceback depth all participate in the algorithm and checker verifies the 3-by-7 scenario/config matrix.
- Stage14 block/continuous comparison: PASS. A_BLOCK_300, B_CONT_50x6, C_CONT_100x3 and D_CONT_150x2 run independently with scheme-specific execution digests.
- Stage15 final plots and Markdown reports: PASS. Three final figures, `stage15_core_questions_answer.md`, `stage15_all_figures_guide.md` and `stage15_final_summary_report.md` were generated.

## Gate

PASS_CC_S3_INTEGRATION

## Notes

The SNR axis is `SNR = Es/N0 (dB)`. The model is symbol-level discrete BPSK-AWGN, not a full continuous-time waveform simulation with oversampling, pulse shaping or receive filtering.
