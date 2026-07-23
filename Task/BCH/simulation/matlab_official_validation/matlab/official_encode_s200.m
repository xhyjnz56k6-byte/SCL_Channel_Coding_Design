function encoded = official_encode_s200(payload)
% Encode one or more 200-bit payload rows with official BCH(15,11).
if size(payload,2) ~= 200
    error('BCH16V:S200PayloadLength','S200 payload must have 200 columns');
end
padded = [double(payload), zeros(size(payload,1),9)];
segments = reshape(padded.',11,[]).';
official = double(bchenc(gf(segments),15,11,'end').x);
encoded = reshape(official.',285,[]).';
end

