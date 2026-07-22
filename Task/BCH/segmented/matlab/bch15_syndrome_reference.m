function syndrome = bch15_syndrome_reference(received)
received = bch15_validate_bits(received, 15, 'received');
[~, syndrome] = bch15_gf2_divide_reference(received, [1 0 0 1 1]);
end
