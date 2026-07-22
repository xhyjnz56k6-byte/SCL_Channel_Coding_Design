function bits = bch15_message_from_decimal(index)
if ~isscalar(index) || index < 0 || index > 2047 || floor(index) ~= index
    error('BCH06:InvalidMessageIndex', 'message index must be an integer in [0,2047].');
end
bits = zeros(1,11);
for p = 1:11
    bits(p) = bitget(uint16(index), 12-p);
end
end
