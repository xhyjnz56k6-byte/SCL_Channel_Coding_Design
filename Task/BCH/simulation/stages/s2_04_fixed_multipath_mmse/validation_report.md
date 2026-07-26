# S2-04 Fixed Multipath MMSE Validation Report

- Functional Gate: PASS_BCH_S2_04_FIXED_MULTIPATH_MMSE_FUNCTIONAL.
- Strict cleanup Gate: PASS_BCH_S2_BATCH1_STRICT_AUDIT_CLEANUP.
- Formal summary SHA256 unchanged: ECDAB168917C606B9ED06805463E1DECE7F0F3C5E129B3800B5EA71845C5B649.
- Formal was not rerun in strict cleanup; preserved 145 points and 2653721 frames.
- noisePairingStatus=DETERMINISTIC_PER_CASE_NOT_STRICTLY_PAIRED_BY_PHYSICAL_SNR.
- Current formal rows remain deterministic standard Gaussian per case and reproducible, but are not strict paired Monte Carlo across cases at the same physical Es/N0/frameIndex.
- noise policy v2 is implemented for subsequent experiments: payloadLength + llround(snrDb*1000) + noisePolicyVersion; S2-04 formal data remains v1.
- PROMPT_DEVIATION_SMOKE_FRAME_COUNT: frozen prompt expected 1000/1000 smoke frames per point, while executed smoke used 500/500 frames per point; formal 145-point data fully supersedes smoke for the final waterfall conclusions.
- FER amplification overlap statuses: BCH-B200=SINGLE_POINT_ONLY(1), BCH-B300=NO_VALID_OVERLAP(0), BCH-B300-426=NO_VALID_OVERLAP(0), BCH-S200=CURVE_ALLOWED(3), BCH-S300=CURVE_ALLOWED(6).
- All snrDb x-axes are rendered as Symbol Es/N0 (dB); figure-data keeps sourcePayloadEbN0Db, frameRate, and snrDb.
- Legend uniqueness audit PASS for 24 figures.
- totalReceiverTimingScope=EQUALIZATION_HARD_DECISION_ERROR_ACCOUNTING_DECODE_AND_AUDIT; avgTotalReceiverTimeUs is complete software receiver processing time and is not defined as pure MMSE time plus pure BCH algorithm time.
- non-PNG artifacts: 0.
- No S2-05/S2-06/S2-07 frequency offset, erasure, or burst-error experiment was started.
- mergeStatus=NOT_MERGED.
