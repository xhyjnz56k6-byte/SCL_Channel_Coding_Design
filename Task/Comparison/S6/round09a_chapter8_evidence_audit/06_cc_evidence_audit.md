# CC_S6_FORMAL_EVIDENCE_AUDIT

Formal source: S6 does not rerun CC Formal. `integrate_cc.py` selects 248 rows from `Task/CC/simulation/stages/S3/stage14_block_continuous_comparison/results/stage14_online_slot_formal_results_all_decisions.csv`; source rows=744; selection=`R12; A_BLOCK_300/B_CONT_50x6/C_CONT_100x3/D_CONT_150x2; Hard/Soft Float`.

Frozen conditions: payload=300, transmittedBits=612, actualRate=0.4901960784. Block rows use D/W/S=306/306/300. Slot rows use D/W/S=70/128/25. Hard inputPrecision=1 bit; float soft inputPrecision=Float.

SNR/noise: `stage14_runner.cpp:528-530` uses symbol-SNR variance. Output writes `snrDb,esN0Db,ebN0Db` at `stage14_runner.cpp:728-796`. S6 figures use `esN0Db`.

Hard definition: received samples are thresholded to 0/1 and depunctured with observed masks (`stage14_runner.cpp:571-596`), then hard Viterbi uses masked expanded bits (`stage14_runner.cpp:612-618`).

Soft definition: soft path calls `decode_terminated_masked_symbols` or sliding-window scheduler with floating depunctured symbols (`stage14_runner.cpp:620-647`). Use term: floating soft-decision Viterbi with continuous received-symbol Euclidean-distance-style branch metric, not LLR Viterbi.

Fairness boundary: hard/soft share code configuration and SNR grid, but integrated summary records non-strict pair-stop, and source is S3 Stage14 reuse/integration rather than fresh paired S6 Formal. State this in Chapter 8.

Complexity/timing: ACS and traceback are separate counters (`stage14_runner.cpp:62-63,631-633,661-662,854-856`). CPU decode timing starts before decoder call (`stage14_runner.cpp:610`) and ends after decoder returns (`stage14_runner.cpp:681-684`). First-output and decision delays are symbol-schedule latencies, not CPU decode time.
