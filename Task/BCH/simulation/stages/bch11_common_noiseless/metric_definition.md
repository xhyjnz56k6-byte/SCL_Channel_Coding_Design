# BCH Group 4 metric definition

- `decodedBitErrors`: Hamming distance between original and recovered payload.
- `frameError`: `decodedBitErrors > 0`.
- BER/FER denominators use processed payload bits/frames only.
- `trueSuccess`: recovered payload equals original payload.
- `reportedSuccess`: the decoder reports success under the adapter contract.
- `miscorrected`: reported success with an incorrect recovered payload.
- `decoderFailure`: decoder does not report success.
- Channel hard errors compare hard-decision bits with the transmitted BCH codeword.

Every result must satisfy truth/frame and report/failure partitions and all rates must be in [0,1].
