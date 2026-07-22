# BCH-06 MATLAB independent reference

The stage independently implements BCH(15,11,1) GF(2) long division, systematic encoding, syndrome calculation, a 15-entry lookup decoder, and S200/S300 segmented recovery in MATLAB. MATLAB never reads C++ output as algorithm input; C++ outputs are only compared afterwards by Python.

Allowed scope is MATLAB reference code, BCH-06 scripts/configuration, the read-only C++ export target, CMake registration, and this stage's audit records. No BCH-02–05 algorithm, Common, BCH-07, AWGN, BPSK, whole-block BCH, BM, Chien, or generic GF module is changed.

| Requirement | Implementation | Positive check | Gate |
|---|---|---|---|
| GF(2) independent reference | `matlab/bch15_gf2_divide_reference.m` | 2048 encodes | mismatch 0 |
| Lookup reference | MATLAB lookup functions | 2048 no error + 30720 single error | mismatch 0 |
| Segmented reference | MATLAB segmented functions | 208 frames, 705 single errors | mismatch 0 |
| Cross-language detail check | C++ exporter + Python checker | CSV fields and row order | mismatch 0 |
