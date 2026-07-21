# MATLAB validation plan (future work)

BCH-02/03 will create deterministic message/reference-codeword vectors under the frozen bit order and compare them to MATLAB BCH facilities or an independently reviewed MATLAB polynomial reference. Decoder stages will compare no-noise, `syndrome=0 -> NO_ERROR`, every one of the 15 nonzero single-bit syndromes and their error positions, selected multi-error audit vectors, and recovered payload ordering. Whole-block parameters and shortening will be confirmed separately before BM/Chien implementation.

No MATLAB command was run in BCH-01; this is a plan, not evidence of validation.
