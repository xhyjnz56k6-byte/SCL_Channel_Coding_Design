# CC S3 core questions

All values below come from `stage15_final_scheme_matrix.csv`; the channel is
symbol-level discrete BPSK-AWGN, not a continuous-time waveform simulation.

## 1. R12/R23/R34 reliability versus throughput

- R12: Es/N0=-0.5 dB 时 FER=0.070274，actual-rate goodput=0.45575。
- R23: Es/N0=2.5 dB 时 FER=0.00154，actual-rate goodput=0.65259。
- R34: Es/N0=3.5 dB 时 FER=0.00146，actual-rate goodput=0.73422。

Use fields `snrDb`, `FER`, and `normalizedGoodput`; see
`stage15_final_fer.png` and `stage15_goodput_fer_pareto.png`. Higher rates
raise the high-SNR throughput ceiling but require more Es/N0 for the same FER.

## 2. Hard, Float and quantized Soft

The Q8 recommendation and its exact SNR losses are recorded in
`../stage11_soft_quantization/results/stage11_quantization_snr_loss.csv`.
Use `decisionMode`, `quantMode`, `BER`, `FER`, `avgDecodeTimeUs` and memory
fields; see `stage15_final_ber.png`, `stage15_quantization_snr_loss.png`.
Float is the reference; quantized modes trade input representation for the
measured loss. Hard decisions remain useful only where simplicity dominates.

## 3. Block, 50×6, 100×3 and 150×2

Use Stage14 fields `firstOutputDelaySymbols`, `p95DecisionDelaySymbols`,
`peakRxBufferSymbols`, `outputBatchCount` and `FER`. The selected organization
is data-driven in `stage14_organization_recommendations.csv`; see Stage14
per-rate plots. Reliability differences within confidence intervals do not
erase the measured scheduling, output-rhythm and buffering differences.

## 4. Full, truncated and sliding-window

Use `tracebackMode`, `dtb`, `window`, `slide`, `FER`, delay, memory, ACS and
traceback-operation fields. See `stage15_traceback_memory_reliability.png`
and all Stage13 final comparison plots. Full traceback is the reference;
truncated D84/D112 and bounded true windows are accepted only when their
measured reliability Gate passes.

## 5. Q, Dtb, W and S configuration

Stage11 selected Q8. Stage10's formal finite-depth result and Stage13's
per-rate performance/latency/memory/balanced selections are preserved in
their recommendation CSVs. No Q, Dtb, W, S or slot organization was fixed
before measurement.

## Final objective-specific recommendations

| recommendationType | schemeId | rate | decisionMode | quantMode | dtb | window | slide | organization | snrDb | FER | normalizedGoodput | firstOutputDelaySymbols | totalMemoryBytes | tracebackOperations | avgDecodeTimeUs | applicability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reliability_first | R34_S_BLOCK_FULL | R34 | Soft Float | Float | 306 | 306 | 300 | Block300 | 3.5 | 0.0014599999999999 | 0.7342205882352941 | nan | nan | nan | 342.3420060000013 | symbol-level discrete BPSK-AWGN; select only when the measured SNR/FER operating region is covered |
| throughput_first | R34_S_BLOCK_FULL | R34 | Soft Float | Float | 306 | 306 | 300 | Block300 | 3.5 | 0.0014599999999999 | 0.7342205882352941 | nan | nan | nan | 342.3420060000013 | symbol-level discrete BPSK-AWGN; select only when the measured SNR/FER operating region is covered |
| latency_first | R34_CONTROL_D_W160_S16_D35 | R34 | Soft Float | Float | 35 | 160 | 16 | Continuous300 | 2.0 | 0.1328320802005012 | 0.6376234704408079 | 66.0 | 32256.0 | 1832208.0 | 2046.014751163617 | symbol-level discrete BPSK-AWGN; select only when the measured SNR/FER operating region is covered |
| memory_first | R12_CONTINUOUS_TRUNCATED_D84 | R12 | Soft Float | Float | 84 | 0 | 300 | Continuous300 | -0.5 | 0.0672494956287827 | 0.45723063939765546 | 166.0 | 17664.0 | 55708968.0 | 571.7184599865502 | symbol-level discrete BPSK-AWGN; select only when the measured SNR/FER operating region is covered |
| complexity_first | R23_BLOCK_FULL_TRACEBACK | R23 | Soft Float | Float | 306 | 306 | 300 | Block300 | 1.0 | 0.0930665425779432 | 0.5927669656353312 | 457.0 | 60288.0 | 657594.0 | 302.6525825965561 | symbol-level discrete BPSK-AWGN; select only when the measured SNR/FER operating region is covered |
| balanced | R34_SLIDING_LATENCY_FIRST | R34 | Soft Float | Float | 98 | 128 | 25 | Continuous300 | 2.0 | 0.0723236663086287 | 0.6821149512436553 | 162.0 | 26112.0 | 3044370.0 | 1081.4575008950956 | symbol-level discrete BPSK-AWGN; select only when the measured SNR/FER operating region is covered |

Limit: CPU times describe this Release build, host, OS and compiler; they are
not universal hardware constants.
