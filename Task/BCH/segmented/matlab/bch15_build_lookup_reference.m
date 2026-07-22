function table = bch15_build_lookup_reference()
table = struct('syndrome', cell(1,15), 'syndromeBits', cell(1,15), 'errorPosition', cell(1,15), 'errorPattern', cell(1,15));
for p = 0:14
    errorPattern = zeros(1,15); errorPattern(p+1) = 1;
    syndromeBits = bch15_syndrome_reference(errorPattern);
    table(p+1).syndrome = bch15_syndrome_value(syndromeBits);
    table(p+1).syndromeBits = syndromeBits;
    table(p+1).errorPosition = p;
    table(p+1).errorPattern = errorPattern;
end
end
