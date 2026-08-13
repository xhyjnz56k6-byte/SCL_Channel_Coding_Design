# S6_SNR_CONVENTION_AUDIT

Finding: Chapter 8 should call the x-axis `Es/N0` / symbol SNR Es/N0 (dB), not a unified Eb/N0 axis.

BCH: `run_bch_formal.ps1` passes `--esn0-db`. `bch_awgn_simulation.cpp:286-291` checks variance `1/(2*10^(Es/N0/10))` when `esN0IsPrimary`; `bch_awgn_simulation.cpp:421-427` writes both `esN0Db` and derived `ebn0Db`. BCH derived Eb/N0 differs by scheme rate: S200=200/285, B200=200/248.

CC: `stage14_runner.cpp:528-530` uses `sigma_squared=1/(2*10^(snr/10))`; output columns include `snrDb,esN0Db,ebN0Db` at `stage14_runner.cpp:728-796`. S6 figures use `esN0Db`; Eb/N0 is derived with fixed R=300/612.

LDPC: `s4_ldpc.cpp:470-488` receives `esN0Db`, uses `sigmaSquared=1/(2*10^(Es/N0/10))`, BPSK +/-1, and LLR `2*received/sigmaSquared`. `main.cpp:323-325` writes `esN0Db=snr` and `ebN0Db=snr-10log10(actualRate)`. N560 actual rate is 300/560.

Cross-family use: compare on Es/N0 only. Do not silently mix derived Eb/N0 across modules.
