function [quotient, remainder] = bch15_gf2_divide_reference(dividend, divisor)
dividend = bch15_validate_bits(dividend, numel(dividend), 'dividend');
divisor = bch15_validate_bits(divisor, numel(divisor), 'divisor');
if divisor(1) ~= 1, error('BCH06:InvalidDivisor', 'divisor leading coefficient must be one.'); end
if numel(dividend) < numel(divisor), error('BCH06:InvalidDividend', 'dividend must not be shorter than divisor.'); end
work = dividend; quotient = zeros(1, numel(dividend)-numel(divisor)+1);
for i = 1:numel(quotient)
    if work(i) == 1
        quotient(i) = 1;
        work(i:i+numel(divisor)-1) = xor(work(i:i+numel(divisor)-1), divisor);
    end
end
remainder = work(end-numel(divisor)+2:end);
end
