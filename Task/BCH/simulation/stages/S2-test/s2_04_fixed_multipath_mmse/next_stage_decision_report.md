# Next Stage Decision Report

- Status: wait for user confirmation before S2-05/S2-06/S2-07.
- Current-data noise pairing: DETERMINISTIC_PER_CASE_NOT_STRICTLY_PAIRED_BY_PHYSICAL_SNR.
- Current performance ordering and bracketed FER conclusions remain usable, but strict paired Monte Carlo across cases requires new v2-policy runs.
- Recommended next experiment policy: noisePolicyVersion=2 with payloadLength, quantized physical Symbol Es/N0 in milli-dB, and policy version in the noise group.
- Do not claim that the preserved v1 formal data shares identical Gaussian z samples across cases at the same physical Es/N0 and frameIndex.
