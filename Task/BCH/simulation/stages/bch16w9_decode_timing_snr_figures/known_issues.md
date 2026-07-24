# Known issues

1. Decode timing is a software measurement specific to the current Windows host,
   MinGW Release build and current system load. It must not be presented as FPGA,
   ASIC or real-time hardware latency.
2. Individual 5000-frame repetitions show Windows scheduling variation. Published
   values use the frozen three-repeat median without smoothing.
3. `Task/BCH/simulation/results/bch16w9_decode_timing_snr_figures/run_20260724_01`
   is an incomplete, ignored experimental directory caused by an outer command
   timeout. Only `run_20260724_02` is valid and published.
4. BER/FER values come from the already validated W8 formal summary. They were not
   resimulated; only the exact rate-aware SNR horizontal coordinate was derived.
5. Stage-C manifest, final audit report, functional commit, push and remote
   verification have not been performed.
