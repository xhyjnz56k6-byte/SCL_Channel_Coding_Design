function detail = bch15_lookup_decode_reference(received, table)
received = bch15_validate_bits(received, 15, 'received');
before = bch15_syndrome_reference(received); value = bch15_syndrome_value(before);
detail.correctedCodeword = received; detail.syndromeBefore = before; detail.correctedPosition = -1; detail.lookupHit = false;
if value == 0
    detail.status = 'NO_ERROR'; detail.syndromeAfter = before;
else
    position = -1;
    for i=1:numel(table), if table(i).syndrome == value, position = table(i).errorPosition; break; end, end
    if position < 0
        detail.status = 'UNRECOGNIZED_SYNDROME'; detail.syndromeAfter = before;
    else
        detail.lookupHit = true; detail.correctedPosition = position;
        if position > 14
            detail.status = 'POST_CHECK_FAILED'; detail.syndromeAfter = before;
        else
            detail.correctedCodeword(position+1) = xor(detail.correctedCodeword(position+1), 1);
            detail.syndromeAfter = bch15_syndrome_reference(detail.correctedCodeword);
            if bch15_syndrome_value(detail.syndromeAfter) == 0, detail.status = 'CORRECTED_SINGLE_ERROR'; else, detail.status = 'POST_CHECK_FAILED'; end
        end
    end
end
detail.decodedMessage = detail.correctedCodeword(1:11);
end
