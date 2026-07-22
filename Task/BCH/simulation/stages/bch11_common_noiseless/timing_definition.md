# Timing definition

Encode and decode duration use `std::chrono::steady_clock` around only the codec call. File input,
CSV output, progress refresh, checkpoint handling, plotting, and Python orchestration are excluded.
BCH-11 establishes the contract; quantile sampling and reported timing statistics are implemented
and validated in the AWGN stages.
