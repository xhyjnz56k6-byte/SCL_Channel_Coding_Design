# Validation

CMake build passed. CTest passed `bch15_encoder` and `bch15_syndrome_table`. The syndrome test verifies all 2048 legal codewords have zero syndrome, all 15 single-error syndromes are nonzero and unique, all positions reverse lookup, and syndrome zero is absent from the table.
