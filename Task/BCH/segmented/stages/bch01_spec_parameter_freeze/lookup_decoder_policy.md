# Syndrome lookup decoder policy

The official segmented decoder is a BCH(15,11,1) syndrome lookup table. It handles `syndrome=0` separately as `NO_ERROR`; syndrome zero never maps to an error position. The error-position lookup table contains exactly 15 nonzero single-bit syndromes (`entryCount=15`), one for each codeword position. BCH-03/04 may use the table only for this segmented case. Double and higher errors are recorded for miscorrrection/uncorrectable auditing; no claim is made that all double errors are reliably detected.
