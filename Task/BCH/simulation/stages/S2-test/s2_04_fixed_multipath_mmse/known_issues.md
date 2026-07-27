# Known issues

- noisePairingStatus=DETERMINISTIC_PER_CASE_NOT_STRICTLY_PAIRED_BY_PHYSICAL_SNR: current S2-04 formal data uses the legacy per-case deterministic noise key, not strict cross-case pairing by physical Es/N0.
- This does not bias each single Monte Carlo BER/FER estimate, and reruns remain reproducible, but cross-case paired-noise claims must not be made for the preserved data.
- PROMPT_DEVIATION_SMOKE_FRAME_COUNT is disclosed: smoke frame count differed from the frozen prompt; formal 145-point, 2,653,721-frame data remains the basis of the reported curves.
- Frequency offset, erasure, and burst-error S2 follow-up experiments were not run.
