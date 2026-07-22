function bits = bch15_validate_bits(bits, expectedLength, name)
if nargin < 3, name = 'bits'; end
if ~isrow(bits) || numel(bits) ~= expectedLength || ~isnumeric(bits) && ~islogical(bits) || any(bits ~= 0 & bits ~= 1)
    error('BCH06:InvalidBits', '%s must be a 1-by-%d binary row vector.', name, expectedLength);
end
bits = double(bits);
end
