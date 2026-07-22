# BCH-06 CSV schema

`*_encoder_reference.csv`: messageIndex, messageBits, parityBits, codewordBits, syndromeBits, syndromeValue.

`*_syndrome_reference.csv`: errorPosition, syndromeBits, syndromeValue.

`*_no_error_decode.csv`: messageIndex, messageBits, receivedBits, syndromeBefore, syndromeAfter, lookupHit, correctedPosition, status, correctedCodeword, decodedMessage.

`*_single_error_decode.csv`: messageIndex, errorPosition, receivedBits, syndromeBefore, syndromeAfter, lookupHit, correctedPosition, status, correctedCodeword, decodedMessage.
