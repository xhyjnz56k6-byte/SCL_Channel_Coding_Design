function value = bch15_syndrome_value(syndrome)
syndrome = bch15_validate_bits(syndrome, 4, 'syndrome');
value = syndrome * [8;4;2;1];
end
