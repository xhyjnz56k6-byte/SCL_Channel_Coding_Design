function codeword = bch15_encode_reference(message)
message = bch15_validate_bits(message, 11, 'message');
[~, remainder] = bch15_gf2_divide_reference([message zeros(1,4)], [1 0 0 1 1]);
codeword = [message remainder];
end
